"""Regras versionadas: carga, validação, hash estável e vigência."""
import json
import shutil
from decimal import Decimal

import pytest

from worker.config import load_settings
from worker.engine.rules import RulesError, load_rules


def test_rules_load_with_version_and_hash(rules):
    assert rules.version == "2026.1.0"
    assert len(rules.hash) == 64
    assert sorted(rules.anexos) == ["I", "II", "III", "IV", "V"]
    assert rules.verified["simples"] is True
    assert rules.verified["presumido"] is False   # LC 224 lida só em fontes secundárias


def test_hash_is_stable(rules):
    again = load_rules(load_settings().rules_dir, "2026")
    assert again.hash == rules.hash


@pytest.mark.parametrize("anexo", ["I", "II", "III", "IV", "V"])
def test_every_band_shares_sum_to_one(rules, anexo):
    for band in rules.anexos[anexo].bands:
        assert abs(sum(band.shares.values()) - 1) <= Decimal("0.0001")


def test_anexo_i_band6_matches_official_table(rules):
    band = rules.anexos["I"].band_number(6)
    assert (band.nominal, band.deduzir) == (Decimal("0.19"), Decimal("378000.00"))
    assert band.share("irpj") == Decimal("0.135") and band.share("icms") == 0
    assert rules.anexos["I"].band_number(5).share("icms") == Decimal("0.335")


def test_vigencia_2026_only(rules):
    assert rules.in_force("2026-01") and rules.in_force("2026-12")
    assert not rules.in_force("2025-12") and not rules.in_force("2027-01")


def test_invalid_rule_file_is_rejected(tmp_path):
    src = load_settings().rules_dir
    dst = tmp_path / "rules"
    shutil.copytree(src, dst)
    simples = dst / "2026" / "simples.json"
    data = json.loads(simples.read_text(encoding="utf-8"))
    data["anexos"]["I"]["faixas"][0]["reparticao"][0] = "0.5"      # repartição deixa de somar 100%
    simples.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RulesError, match="repartição soma"):
        load_rules(dst, "2026")


def test_changed_rule_changes_hash(tmp_path, rules):
    dst = tmp_path / "rules"
    shutil.copytree(load_settings().rules_dir, dst)
    manifest = dst / "2026" / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["version"] = "2026.1.1"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    assert load_rules(dst, "2026").hash != rules.hash
