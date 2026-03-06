import os
import sys
import tempfile
import json


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from eval_utils import extract_terraform_code
from spec_checker import DeleteValidation
from compute_metrics import compute_metrics_for_folder
from eval_core import extract_compact_state


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


def test_extract_compact_state_returns_minimal_resource_view():
    tfstate = {
        "resources": [
            {
                "type": "xenorchestra_vm",
                "name": "vm",
                "instances": [{"attributes": {"id": "vm-123", "name_label": "web-01"}}]
            }
        ]
    }

    compact = extract_compact_state(json.dumps(tfstate))
    parsed = json.loads(compact)
    assert parsed == [{"type": "xenorchestra_vm", "name": "vm", "id": "vm-123"}]


def test_reference_and_csv_provider_urls_use_api_suffix():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ref_file = os.path.join(repo_root, "tasks", "references", "C1.1.tf")
    csv_file = os.path.join(repo_root, "tasks", "vm_provisioning_tasks.csv")

    with open(ref_file, "r", encoding="utf-8") as f:
        ref_text = f.read()
    with open(csv_file, "r", encoding="utf-8") as f:
        csv_text = f.read()

    assert 'url      = "ws://localhost:8080/api/"' in ref_text
    assert 'url      = ""ws://localhost:8080/api/""' in csv_text
