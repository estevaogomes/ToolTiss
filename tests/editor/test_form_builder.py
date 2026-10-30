import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from editor.services.form_builder import FormBuilder

XML_SADT_MINIMO = b'''<?xml version="1.0" encoding="iso-8859-1"?>
<ans:mensagemTISS xmlns:ans="http://www.ans.gov.br/padroes/tiss/schemas">
    <ans:cabecalho>
        <ans:identificacaoTransacao>
            <ans:tipoTransacao>ENVIO_LOTE_GUIAS</ans:tipoTransacao>
            <ans:sequencialTransacao>14584688</ans:sequencialTransacao>
            <ans:dataRegistroTransacao>2026-09-30</ans:dataRegistroTransacao>
            <ans:horaRegistroTransacao>23:56:35</ans:horaRegistroTransacao>
        </ans:identificacaoTransacao>
        <ans:origem>
            <ans:identificacaoPrestador>
                <ans:codigoPrestadorNaOperadora>68870</ans:codigoPrestadorNaOperadora>
            </ans:identificacaoPrestador>
        </ans:origem>
        <ans:destino>
            <ans:registroANS>304701</ans:registroANS>
        </ans:destino>
        <ans:Padrao>4.03.00</ans:Padrao>
    </ans:cabecalho>
    <ans:prestadorParaOperadora>
        <ans:loteGuias>
            <ans:numeroLote>28595</ans:numeroLote>
            <ans:guiasTISS>
                <ans:guiaSP-SADT>
                    <ans:cabecalhoGuia>
                        <ans:registroANS>304701</ans:registroANS>
                        <ans:numeroGuiaPrestador>1557971967</ans:numeroGuiaPrestador>
                        <ans:guiaPrincipal>1557971967</ans:guiaPrincipal>
                    </ans:cabecalhoGuia>
                    <ans:dadosBeneficiario>
                        <ans:numeroCarteira>00320000065565592</ans:numeroCarteira>
                        <ans:atendimentoRN>N</ans:atendimentoRN>
                    </ans:dadosBeneficiario>
                    <ans:procedimentosExecutados>
                        <ans:procedimentoExecutado>
                            <ans:sequencialItem>0</ans:sequencialItem>
                            <ans:dataExecucao>2026-09-12</ans:dataExecucao>
                            <ans:procedimento>
                                <ans:codigoProcedimento>146935</ans:codigoProcedimento>
                                <ans:descricaoProcedimento>KIT TESTE</ans:descricaoProcedimento>
                            </ans:procedimento>
                            <ans:quantidadeExecutada>1.0</ans:quantidadeExecutada>
                            <ans:valorUnitario>3980.0</ans:valorUnitario>
                            <ans:valorTotal>3980.00</ans:valorTotal>
                        </ans:procedimentoExecutado>
                    </ans:procedimentosExecutados>
                </ans:guiaSP-SADT>
            </ans:guiasTISS>
        </ans:loteGuias>
    </ans:prestadorParaOperadora>
    <ans:epilogo>
        <ans:hash>abc123</ans:hash>
    </ans:epilogo>
</ans:mensagemTISS>'''


def _write_temp_xml(content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".xml")
    os.write(fd, content)
    os.close(fd)
    return path


def test_xml_to_dict_detects_sadt():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        assert result["tipo"] == "guiaSP-SADT"
    finally:
        os.unlink(path)


def test_xml_to_dict_extracts_cabecalho():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        assert result["cabecalhoGuia"]["registroANS"] == "304701"
        assert result["cabecalhoGuia"]["numeroGuiaPrestador"] == "1557971967"
    finally:
        os.unlink(path)


def test_xml_to_dict_extracts_procedimentos_as_list():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        procs = result["procedimentosExecutados"]
        assert isinstance(procs, list)
        assert len(procs) == 1
        assert procs[0]["sequencialItem"] == "0"
        assert procs[0]["codigoProcedimento"] == "146935"
        assert procs[0]["valorTotal"] == "3980.00"
    finally:
        os.unlink(path)


def test_xml_to_dict_excludes_hash():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        assert "hash" not in result
        assert "epilogo" not in result
    finally:
        os.unlink(path)


def test_xml_to_dict_preserves_namespaces():
    path = _write_temp_xml(XML_SADT_MINIMO)
    try:
        result = FormBuilder.xml_to_dict(path)
        assert "_namespaces" in result
        assert "ans" in result["_namespaces"]
        assert result["_namespaces"]["ans"] == "http://www.ans.gov.br/padroes/tiss/schemas"
    finally:
        os.unlink(path)
