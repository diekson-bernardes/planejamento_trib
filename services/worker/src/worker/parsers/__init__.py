"""Registro DocType → parser."""
from worker.models import DocType
from worker.parsers.balancete_alterdata import BalanceteAlterdataParser
from worker.parsers.base import Parser
from worker.parsers.dre_alterdata import DreAlterdataParser
from worker.parsers.folha_alterdata import FolhaAlterdataParser
from worker.parsers.pgdas import PgdasParser

PARSERS: dict[DocType, Parser] = {
    DocType.PGDAS_D: PgdasParser(),
    DocType.FOLHA_ALTERDATA: FolhaAlterdataParser(),
    DocType.DRE_ALTERDATA: DreAlterdataParser(),
    DocType.BALANCETE_ALTERDATA: BalanceteAlterdataParser(),
}


def get_parser(doc_type: DocType) -> Parser:
    return PARSERS[doc_type]
