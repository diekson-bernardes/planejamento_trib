"""Encargos patronais sobre a folha por regime (CPP, RAT × FAP, terceiros)."""
from decimal import Decimal

from worker.engine.assumptions import Assumptions
from worker.engine.memory import D, ZERO, Line, brl, money, pct
from worker.engine.rules import RuleSet
from worker.engine.snapshot import SnapshotView


def payroll_bases(view: SnapshotView, comp: str) -> dict:
    """Bases da folha (Resumo Geral Alterdata, página 2 — informações auxiliares)."""
    def pick(*keys):
        for k in keys:
            v = view.get("FOLHA_ALTERDATA", comp, k)
            if v:
                return D(v["value"]), view.origin(v)
        return ZERO, {}

    empregados, o_emp = pick("aux.base_empregados", "fgts.base_sem_13")
    socios, o_soc = pick("auxiliares.base_socios")
    autonomos, o_aut = pick("auxiliares.base_autonomos")
    return {
        "empregados": (empregados, o_emp),
        "socios": (socios, o_soc),
        "autonomos": (autonomos, o_aut),
    }


def charges(regime: str, comp: str, view: SnapshotView, a: Assumptions, rules: RuleSet,
            share: Decimal = Decimal("1"), label: str = "") -> list[Line]:
    """Encargos do regime na competência. `share` proporcionaliza (Anexo IV em empresa com vários anexos)."""
    enc = rules.encargos
    bases = payroll_bases(view, comp)
    emp, o_emp = bases["empregados"]
    soc, o_soc = bases["socios"]
    aut, o_aut = bases["autonomos"]
    cpp_rate = D(enc["cpp"])
    rat = a.decimal("folha.rat", default=D(enc["rat_sugerido"]))
    fap = a.decimal("folha.fap", default=D(enc["fap_sugerido"]))
    terceiros = a.decimal("folha.terceiros", default=ZERO)
    verified = rules.verified.get("encargos", False)
    suffix = f" × participação {pct(share, 2)}" if share != 1 else ""
    lines = []

    cpp_base = (emp + soc + aut) * share
    lines.append(Line(regime, comp, "cpp", money(cpp_base), cpp_rate, money(cpp_base * cpp_rate),
                      f"(empregados {brl(emp)} + sócios {brl(soc)} + autônomos {brl(aut)}){suffix} × CPP {pct(cpp_rate, 2)}{label}",
                      rules.ref("encargos", "cpp"), origin={"empregados": o_emp, "socios": o_soc, "autonomos": o_aut},
                      verified=verified))
    rat_rate = rat * fap
    lines.append(Line(regime, comp, "rat", money(emp * share), rat_rate, money(emp * share * rat_rate),
                      f"empregados {brl(emp)}{suffix} × RAT {pct(rat, 2)} × FAP {fap}{label}",
                      rules.ref("encargos", "rat"), origin={"base": o_emp, "rat": a.origin("folha.rat"), "fap": a.origin("folha.fap")},
                      verified=verified))
    if not regime.startswith("SIMPLES") or rules.encargos["simples_anexo_iv"]["terceiros"]:
        lines.append(Line(regime, comp, "terceiros", money(emp * share), terceiros, money(emp * share * terceiros),
                          f"empregados {brl(emp)}{suffix} × terceiros {pct(terceiros, 2)}{label}",
                          rules.ref("encargos", "terceiros"), origin={"base": o_emp, "aliquota": a.origin("folha.terceiros")},
                          verified=verified))
    return lines
