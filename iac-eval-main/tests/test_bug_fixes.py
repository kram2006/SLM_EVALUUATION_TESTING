import os
import sys
import tempfile


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from eval_utils import extract_terraform_code
from spec_checker import DeleteValidation
from compute_metrics import compute_metrics_for_folder


def test_extract_terraform_code_keeps_non_empty_when_language_line_has_no_newline():
    assert extract_terraform_code("```hcl```") == "hcl"


def test_extract_terraform_code_parses_hcl_block_with_language_tag():
    response = "```hcl\nresource \"x\" \"y\" {}\n```"
    assert extract_terraform_code(response) == 'resource "x" "y" {}'


def test_delete_validation_checks_target_vm_names():
    validator = DeleteValidation()
    vm_resources = [
        {"action": "delete", "name_label": "web-01"},
        {"action": "delete", "name_label": "web-02"},
    ]
    specs = {"delete_count": 2, "target_vms": ["web-02", "web-03"]}

    errors, checks, _ = validator.validate(vm_resources, specs)

    assert "correct_vms_targeted" in checks
    assert any("Target VM 'web-03'" in e for e in errors)
    assert any("Extra VMs deleted" in e for e in errors)


def test_compute_metrics_exits_when_evaluation_lockfile_exists(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, ".evaluation_in_progress"), "w").close()
        csv_path = os.path.join(tmpdir, "tasks.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("task_id,reference_hcl\n")

        result = compute_metrics_for_folder(tmpdir, csv_path)

        out = capsys.readouterr().out
        assert result is None
        assert "Evaluation still running" in out
