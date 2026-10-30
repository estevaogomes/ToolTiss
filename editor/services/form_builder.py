"""Bidirectional conversion between TISS XML and structured dicts."""
import io
import re
import xml.etree.ElementTree as ET
from typing import Union

# Tags whose children are always lists (repeating elements)
LIST_TAGS = {
    "procedimentoExecutado", "despesa", "diagnostico",
    "profissionalExecutante", "equipeSadt", "motivoGlosa",
}

# Wrapper tags whose leaf-only children should be flattened into the parent dict
FLATTEN_TAGS = {
    "procedimento", "dadosBeneficiario", "identificacaoPrestador",
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
        # Merge guia fields into result
        for key, value in guia_dict.items():
            # Map cabecalhoGuia -> cabecalho for consistent form access
            out_key = "cabecalho" if key == "cabecalhoGuia" else key
            result[out_key] = value

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
    def dict_to_xml(dados: dict, output_path: str) -> str:
        """Convert a structured dict back to TISS XML file.

        Recalculates hash via TissXmlService.atualizar_hash_tiss().
        Returns the generated hash string.
        """
        # Implementation deferred to next task — stub for now
        raise NotImplementedError("dict_to_xml will be implemented in Task 4")
