"""Bidirectional conversion between TISS XML and structured dicts."""
import hashlib
import io
import re
import xml.etree.ElementTree as ET
from typing import Union

# Tags whose children are always lists (repeating elements)
LIST_TAGS = {
    "procedimentoExecutado", "procedimentoRealizado", "despesa", "diagnostico",
    "profissionalExecutante", "equipeSadt", "motivoGlosa",
}

# Wrapper tags whose leaf-only children should be flattened into the parent dict
FLATTEN_TAGS = {
    "procedimento", "identificacaoPrestador",
    "identificacaoTransacao", "origem", "destino",
}

# Map tag local names to dict keys for known guia types
GUIA_TYPE_MAP = {
    "guiaSP-SADT": "guiaSP-SADT",
    "guiaHonorarios": "guiaHonorarios",
    "guiaResumoInternacao": "guiaResumoInternacao",
}


class FormBuilder:
    """Converts TISS XML files to/from structured Python dicts."""

    @staticmethod
    def xml_to_dict(xml_path: str) -> dict:
        """Parse a TISS XML file and return a structured dict.

        Returns dict with keys: tipo, cabecalho, <guia fields>, _namespaces.
        Excludes <epilogo> and <hash> (hash is recalculated on save).
        """
        # Single I/O pass: read file bytes once, extract namespaces from
        # raw XML declarations, then parse the tree from the same bytes.
        with open(xml_path, "rb") as f:
            raw_bytes = f.read()

        namespaces = {}
        header = raw_bytes[:4096].decode("iso-8859-1", errors="replace")
        for match in re.finditer(r'xmlns:(\w+)="([^"]+)"', header):
            namespaces[match.group(1)] = match.group(2)

        parser = ET.XMLParser(encoding="iso-8859-1")
        tree = ET.parse(io.BytesIO(raw_bytes), parser)
        root = tree.getroot()

        result = {"_namespaces": namespaces}

        # Find the guia element (inside guiasTISS) — process first so
        # cabecalhoGuia maps to "cabecalho" before any transaction header
        guia_elem = None
        guia_tipo = None
        for elem in root.iter():
            tag_local = elem.tag.split("}")[-1]
            if tag_local in GUIA_TYPE_MAP:
                guia_elem = elem
                guia_tipo = GUIA_TYPE_MAP[tag_local]
                break

        if guia_elem is None:
            raise ValueError(
                f"Guia type not found. Expected one of: {list(GUIA_TYPE_MAP.keys())}"
            )

        result["tipo"] = guia_tipo
        guia_dict = FormBuilder._elem_to_dict(guia_elem)
        # Merge guia fields into result (preserve original XML tag names)
        for key, value in guia_dict.items():
            result[key] = value

        return result

    @staticmethod
    def _elem_to_dict(elem) -> Union[dict, str, list]:
        """Recursively convert an ElementTree element to dict/list/string.

        - Leaf nodes (no children) -> stripped text string
        - Nodes with repeating children (LIST_TAGS) -> list of dicts
        - Other nodes -> dict of child tag -> value
        - Skips epilogo and hash tags entirely
        """
        tag_local = elem.tag.split("}")[-1]

        # Skip epilogo and hash
        if tag_local in ("epilogo", "hash"):
            return None

        children = list(elem)
        if not children:
            # Leaf node
            return (elem.text or "").strip()

        # Check if this element contains repeating children that should be a list
        child_tags = [c.tag.split("}")[-1] for c in children]
        has_repeating = any(tag in LIST_TAGS for tag in child_tags)

        if has_repeating:
            # Check if ALL non-skipped children are repeating LIST_TAGS
            # If so, this wrapper element becomes a list directly
            non_skip_children = [c for c in children if c.tag.split("}")[-1] not in ("epilogo", "hash")]
            all_repeating = all(c.tag.split("}")[-1] in LIST_TAGS for c in non_skip_children)

            if all_repeating and len(non_skip_children) > 0:
                # Wrapper element flattens to a list of its children
                items = []
                for child in non_skip_children:
                    child_value = FormBuilder._elem_to_dict(child)
                    if child_value is not None:
                        items.append(child_value)
                return items
            else:
                # Build dict but convert repeating children to lists
                result = {}
                list_accumulator = {}
                for child in children:
                    child_tag = child.tag.split("}")[-1]
                    if child_tag in ("epilogo", "hash"):
                        continue
                    child_value = FormBuilder._elem_to_dict(child)
                    if child_value is None:
                        continue
                    if child_tag in LIST_TAGS:
                        if child_tag not in list_accumulator:
                            list_accumulator[child_tag] = []
                        list_accumulator[child_tag].append(child_value)
                    else:
                        result[child_tag] = child_value
                # Merge accumulated lists
                for tag, items in list_accumulator.items():
                    result[tag] = items
                return result
        else:
            # Regular dict — flatten only known wrapper tags whose children are all leaves
            result = {}
            for child in children:
                child_tag = child.tag.split("}")[-1]
                if child_tag in ("epilogo", "hash"):
                    continue
                child_value = FormBuilder._elem_to_dict(child)
                if child_value is None:
                    continue
                # Flatten: only for known wrapper tags with all-leaf string values
                if (child_tag in FLATTEN_TAGS
                        and isinstance(child_value, dict)
                        and all(isinstance(v, str) for v in child_value.values())):
                    for k, v in child_value.items():
                        result[k] = v
                else:
                    result[child_tag] = child_value
            return result

    @staticmethod
    def _extrair_valores_texto_tiss(elemento) -> str:
        """Extract text values from XML tree for ANS TISS hash calculation.

        Mirrors TissXmlService._extrair_valores_texto_tiss but without
        Windows-only imports. Ignores epilogo/hash tags per ANS rules.
        Preserves whitespace in leaf nodes (no strip).
        """
        conteudo = ""
        if elemento.tag.endswith("epilogo") or elemento.tag.endswith("hash"):
            return ""
        if elemento.text and not list(elemento):
            conteudo += elemento.text
        for filho in elemento:
            conteudo += FormBuilder._extrair_valores_texto_tiss(filho)
        return conteudo

    @staticmethod
    def _calcular_hash_tiss(root) -> str:
        """Calculate ANS TISS MD5 hash and update the hash element in-place."""
        tag_hash_alvo = None
        for elem in root.iter():
            if elem.tag.endswith("hash"):
                elem.text = ""
                tag_hash_alvo = elem

        cadeia_valores = FormBuilder._extrair_valores_texto_tiss(root)
        novo_hash = hashlib.md5(cadeia_valores.encode("iso-8859-1")).hexdigest()

        if tag_hash_alvo is not None:
            tag_hash_alvo.text = novo_hash
        return novo_hash

    @staticmethod
    def dict_to_xml(dados: dict, output_path: str) -> str:
        """Convert a structured dict back to TISS XML file.

        Reconstructs the full TISS envelope (mensagemTISS > cabecalho >
        prestadorParaOperadora > loteGuias > guiasTISS > guia) from the
        flat dict produced by xml_to_dict. Preserves original namespaces
        and recalculates the ANS MD5 hash.

        Returns the generated hash string.
        """
        ns = dados.get("_namespaces", {})
        ans_uri = ns.get("ans", "http://www.ans.gov.br/padroes/tiss/schemas")

        # Register namespaces so ET doesn't rename them to ns0/ns1
        for prefix, uri in ns.items():
            ET.register_namespace(prefix, uri)

        # Build root element — register_namespace handles xmlns declarations
        root = ET.Element(f"{{{ans_uri}}}mensagemTISS")
        xsi_uri = ns.get("xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set(
            f"{{{xsi_uri}}}schemaLocation",
            f"{ans_uri} {ans_uri}/tissV4_03_00.xsd",
        )

        # --- Reconstruct cabecalho da transação ---
        cabecalho_elem = ET.SubElement(root, f"{{{ans_uri}}}cabecalho")
        ident_trans = ET.SubElement(cabecalho_elem, f"{{{ans_uri}}}identificacaoTransacao")
        ET.SubElement(ident_trans, f"{{{ans_uri}}}tipoTransacao").text = "ENVIO_LOTE_GUIAS"
        ET.SubElement(ident_trans, f"{{{ans_uri}}}sequencialTransacao").text = "000000"
        ET.SubElement(ident_trans, f"{{{ans_uri}}}dataRegistroTransacao").text = "2000-01-01"
        ET.SubElement(ident_trans, f"{{{ans_uri}}}horaRegistroTransacao").text = "00:00:00"

        origem = ET.SubElement(cabecalho_elem, f"{{{ans_uri}}}origem")
        id_prest = ET.SubElement(origem, f"{{{ans_uri}}}identificacaoPrestador")
        ET.SubElement(id_prest, f"{{{ans_uri}}}codigoPrestadorNaOperadora").text = "00000"

        destino = ET.SubElement(cabecalho_elem, f"{{{ans_uri}}}destino")
        registro_ans = (dados.get("cabecalhoGuia") or {}).get("registroANS", "000000")
        ET.SubElement(destino, f"{{{ans_uri}}}registroANS").text = registro_ans

        ET.SubElement(cabecalho_elem, f"{{{ans_uri}}}Padrao").text = "4.03.00"

        # --- Reconstruct prestadorParaOperadora > loteGuias ---
        ppo = ET.SubElement(root, f"{{{ans_uri}}}prestadorParaOperadora")
        lote = ET.SubElement(ppo, f"{{{ans_uri}}}loteGuias")
        ET.SubElement(lote, f"{{{ans_uri}}}numeroLote").text = "000000"
        guias_tiss = ET.SubElement(lote, f"{{{ans_uri}}}guiasTISS")

        # Determine guia type and build the guia element
        tipo = dados.get("tipo", "guiaSP-SADT")
        guia_elem = ET.SubElement(guias_tiss, f"{{{ans_uri}}}{tipo}")

        # Keys that are metadata, not part of the guia body
        skip_keys = {"_namespaces", "tipo"}

        for key, value in dados.items():
            if key in skip_keys:
                continue
            FormBuilder._dict_to_elem(guia_elem, key, value, ans_uri)

        # --- Epílogo com hash placeholder ---
        epilogo = ET.SubElement(root, f"{{{ans_uri}}}epilogo")
        ET.SubElement(epilogo, f"{{{ans_uri}}}hash").text = ""

        # Recalculate hash
        hash_value = FormBuilder._calcular_hash_tiss(root)

        # Write to file with ISO-8859-1 encoding
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")
        tree.write(output_path, encoding="iso-8859-1", xml_declaration=True)

        return hash_value or ""

    @staticmethod
    def _dict_to_elem(parent, tag: str, value, ns_uri: str) -> None:
        """Recursively convert a dict/list/string value into XML sub-elements.

        For lists, children are added directly to parent with singular tag
        names (no wrapper element). For dicts and strings, a wrapper element
        is created.
        """
        # Known TISS plural -> singular mappings
        singular_map = {
            "procedimentosExecutados": "procedimentoExecutado",
            "procedimentosRealizados": "procedimentoRealizado",
            "outrasDespesas": "outraDespesa",
            "diagnosticos": "diagnostico",
            "profissionais": "profissional",
        }

        if isinstance(value, list):
            # Lists: add each item directly to parent, no wrapper element
            child_tag = singular_map.get(tag, tag.rstrip("s") if tag.endswith("s") else tag)
            for item in value:
                if isinstance(item, dict):
                    child_elem = ET.SubElement(parent, f"{{{ns_uri}}}{child_tag}")
                    for k, v in item.items():
                        FormBuilder._dict_to_elem(child_elem, k, v, ns_uri)
                else:
                    child = ET.SubElement(parent, f"{{{ns_uri}}}{child_tag}")
                    child.text = str(item) if item is not None else ""
        elif isinstance(value, dict):
            elem = ET.SubElement(parent, f"{{{ns_uri}}}{tag}")
            for k, v in value.items():
                FormBuilder._dict_to_elem(elem, k, v, ns_uri)
        elif isinstance(value, str):
            elem = ET.SubElement(parent, f"{{{ns_uri}}}{tag}")
            elem.text = value
        else:
            elem = ET.SubElement(parent, f"{{{ns_uri}}}{tag}")
            elem.text = str(value) if value is not None else ""
