"""Parser do extrato do PGDAS-D (layout da Receita Federal)."""
from worker.classify import classify
from worker.errors import LayoutNotRecognized
from worker.models import DocType, ParseResult, Row
from worker.parsers.base import ValueCollector, find_anchor, label_words, money_words, require_anchor
from worker.pdf.numbers import COMPETENCE, competence_from_mm_yyyy, is_money, parse_money, split_glued

PARSER_VERSION = "pgdas-1.0.0"

TRIBUTOS = ["irpj", "csll", "cofins", "pis", "inss_cpp", "icms", "ipi", "iss", "total"]
TRIBUTO_LABEL = {
    "irpj": "IRPJ", "csll": "CSLL", "cofins": "COFINS", "pis": "PIS/Pasep",
    "inss_cpp": "INSS/CPP", "icms": "ICMS", "ipi": "IPI", "iss": "ISS", "total": "Total",
}
RECEITA_COLS = ["mercado_interno", "mercado_externo", "total"]


class PgdasParser:
    DOC_TYPE = DocType.PGDAS_D
    PARSER_VERSION = PARSER_VERSION

    def parse(self, rows: list[Row], pages: int) -> ParseResult:
        cls = classify(rows, DocType.PGDAS_D)
        if not cls.cnpj or not cls.competence:
            raise LayoutNotRecognized("CNPJ ou período de apuração ausente (parser " + PARSER_VERSION + ")")
        c = ValueCollector(cls.competence)

        i21 = require_anchor(rows, "2.1 Discriminativo de Receitas", PARSER_VERSION)
        i22 = require_anchor(rows, "2.2) Receitas Brutas Anteriores", PARSER_VERSION, i21)
        i221 = require_anchor(rows, "2.2.1) Mercado Interno", PARSER_VERSION, i22)
        i222 = require_anchor(rows, "2.2.2) Mercado Externo", PARSER_VERSION, i221)
        i23 = require_anchor(rows, "2.3) Folha de Salários Anteriores", PARSER_VERSION, i222)
        i24 = require_anchor(rows, "2.4) Fator r", PARSER_VERSION, i23)
        i26 = require_anchor(rows, "2.6) Resumo da Declaração", PARSER_VERSION, i24)
        i27 = require_anchor(rows, "2.7) Informações da Declaração por Estabelecimento", PARSER_VERSION, i26)
        i28 = require_anchor(rows, "2.8) Total Geral da Empresa", PARSER_VERSION, i27)
        i3 = find_anchor(rows, "3. Informações da Recepção", i28) or len(rows)

        self._discriminativo(rows, i21 + 1, i22, c)
        self._series(rows[i221 + 1:i222], "2.2.1", "receita_anterior", "mercado_interno", c)
        self._series(rows[i222 + 1:i23], "2.2.2", "receita_anterior", "mercado_externo", c)
        self._series(rows[i23 + 1:i24], "2.3", "folha_anterior", "folha", c)
        self._resumo(rows, i26, i27, c)
        self._estabelecimentos(rows, i27 + 1, i28, c)
        self._tabelas_totais(rows, i28 + 1, i3, "2.8", c)

        if c.find("receita.rpa") is None or c.find("tributo.total", section="2.8.total_declarado") is None:
            raise LayoutNotRecognized("RPA ou total geral não encontrado (parser " + PARSER_VERSION + ")")

        return ParseResult(
            doc_type=DocType.PGDAS_D, parser_version=PARSER_VERSION, cnpj=cls.cnpj,
            competence=cls.competence, pages=pages, values=c.values,
        )

    # ------------------------------------------------------------------ 2.1
    def _discriminativo(self, rows: list[Row], start: int, stop: int, c: ValueCollector) -> None:
        for idx in range(start, stop):
            row = rows[idx]
            mw = money_words(row)
            if not mw:
                continue
            text = label_words(row)
            nxt = rows[idx + 1].text if idx + 1 < stop else ""
            if "Receita Bruta do PA" in text:
                key, label = "rpa", "Receita Bruta do PA (RPA)"
            elif "Limite de receita" in text:
                key, label = "limite", "Limite de receita bruta proporcionalizado"
            elif "(RBT12p)" in nxt:
                key, label = "rbt12p", "RBT12 proporcionalizada (RBT12p)"
            elif "(RBT12)" in nxt:
                key, label = "rbt12", "Receita bruta acumulada nos 12 meses anteriores (RBT12)"
            elif "(RBAA)" in nxt:
                key, label = "rbaa", "Receita bruta acumulada no ano-calendário anterior (RBAA)"
            elif "(RBA)" in nxt:
                key, label = "rba", "Receita bruta acumulada no ano-calendário corrente (RBA)"
            else:
                raise LayoutNotRecognized("valor sem rótulo na seção 2.1 (parser " + PARSER_VERSION + ")")
            cols = ["total"] if key == "limite" else RECEITA_COLS
            for (w, value, _), col in zip(mw, cols):
                c.add(section="2.1", field_key="receita." + key, label=label, value=value,
                      page=row.page, bbox=w.bbox, column=col)

    # ------------------------------------------------------------------ 2.2 / 2.3
    def _series(self, rows: list[Row], section: str, prefix: str, column: str, c: ValueCollector) -> None:
        for row in rows:
            pending: str | None = None
            for w in row.words:
                token = w.text
                if COMPETENCE.fullmatch(token):
                    pending = token
                    continue
                value_part, glued_comp = split_glued(token)
                if pending and is_money(value_part):
                    value, _ = parse_money(value_part)
                    comp = competence_from_mm_yyyy(pending)
                    c.add(section=section, field_key=prefix + "." + comp,
                          label=prefix.replace("_", " ").capitalize() + " " + pending,
                          value=value, page=row.page, bbox=w.bbox, column=column)
                    pending = glued_comp

    # ------------------------------------------------------------------ 2.6
    def _resumo(self, rows: list[Row], start: int, stop: int, c: ValueCollector) -> None:
        for idx in range(start + 1, stop):
            mw = money_words(rows[idx])
            if len(mw) >= 2:
                (w1, v1, _), (w2, v2, _) = mw[0], mw[1]
                c.add(section="2.6", field_key="resumo.receita_auferida",
                      label="Receita Bruta Auferida", value=v1, page=rows[idx].page, bbox=w1.bbox)
                c.add(section="2.6", field_key="resumo.total_debito_declarado",
                      label="Valor Total do Débito Declarado", value=v2, page=rows[idx].page, bbox=w2.bbox)
                return
        raise LayoutNotRecognized("valores da seção 2.6 ausentes (parser " + PARSER_VERSION + ")")

    # ------------------------------------------------------------------ 2.7
    def _estabelecimentos(self, rows: list[Row], start: int, stop: int, c: ValueCollector) -> None:
        estab = 0
        activity = 0
        section = ""
        description: list[str] = []
        collecting_description = False
        idx = start
        while idx < stop:
            row = rows[idx]
            text = row.text
            if text.startswith("CNPJ Estabelecimento:"):
                estab += 1
                activity = 0
                section = "2.7.estab" + str(estab)
            elif "Sublimite de Receita Anual" in text:
                mw = money_words(row)
                if mw:
                    c.add(section=section, field_key="sublimite", label="Sublimite de Receita Anual",
                          value=mw[0][1], page=row.page, bbox=mw[0][0].bbox)
            elif "Valor do Débito por Tributo para a Atividade" in text:
                activity += 1
                section = "2.7.estab" + str(estab) + ".atividade" + str(activity)
                description = []
                collecting_description = True
            elif text.startswith("Receita Bruta Informada:"):
                collecting_description = False
                mw = money_words(row)
                if not mw:
                    raise LayoutNotRecognized("receita da atividade ausente (parser " + PARSER_VERSION + ")")
                c.add(section=section, field_key="receita_informada", label=" ".join(description),
                      value=mw[0][1], page=row.page, bbox=mw[0][0].bbox)
            elif "Totais do Estabelecimento" in text:
                section = "2.7.estab" + str(estab) + ".total"
            elif text.startswith("Valor Informado:"):
                mw = money_words(row)
                if mw:
                    c.add(section=section, field_key="valor_informado", label="Valor Informado",
                          value=mw[0][1], page=row.page, bbox=mw[0][0].bbox)
            elif self._total_context(text):
                section = "2.7.estab" + str(estab) + "." + self._total_context(text)
            elif text.startswith("IRPJ CSLL") and idx + 1 < stop:
                self._tributos(rows[idx + 1], section, c)
                idx += 1
            elif collecting_description:
                description.append(text)
            idx += 1

    # ------------------------------------------------------------------ 2.8
    def _tabelas_totais(self, rows: list[Row], start: int, stop: int, prefix: str, c: ValueCollector) -> None:
        section = ""
        idx = start
        while idx < stop:
            text = rows[idx].text
            ctx = self._total_context(text)
            if ctx:
                section = prefix + "." + ctx
            elif text.startswith("IRPJ CSLL") and section and idx + 1 < stop:
                self._tributos(rows[idx + 1], section, c)
                idx += 1
            idx += 1

    @staticmethod
    def _total_context(text: str) -> str | None:
        if "Total do Débito Declarado" in text:
            return "total_declarado"
        if "Exigibilidade Suspensa" in text:
            return "total_suspenso"
        if "Total do Débito Exigível" in text:
            return "total_exigivel"
        return None

    @staticmethod
    def _tributos(row: Row, section: str, c: ValueCollector) -> None:
        mw = money_words(row)
        if len(mw) != len(TRIBUTOS):
            raise LayoutNotRecognized(
                "tabela de tributos com " + str(len(mw)) + " colunas (parser " + PARSER_VERSION + ")"
            )
        for (w, value, _), key in zip(mw, TRIBUTOS):
            c.add(section=section, field_key="tributo." + key, label=TRIBUTO_LABEL[key],
                  value=value, page=row.page, bbox=w.bbox, column=key)
