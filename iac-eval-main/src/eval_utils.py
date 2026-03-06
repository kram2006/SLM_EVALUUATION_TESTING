import os
import sys
import time
import subprocess
import logging
import requests
import asyncio
from logger import log_step, log_error

# ANSI Colors for terminal
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
BOLD = "\033[1m"

async def execute_command(command, cwd=None, timeout=None, print_output=True, env=None):
    """Run a shell command asynchronously and return output"""
    try:
        if print_output:
            print(f"{BOLD}{CYAN}> Running: {command}{RESET}")
            
        start_time = time.time()
        
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
            
        # Use asyncio for non-blocking execution
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=run_env
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            stdout = stdout.decode() if stdout else ""
            stderr = stderr.decode() if stderr else ""
        except asyncio.TimeoutExpired:
            try:
                process.kill()
                await process.wait() # CRITICAL: Reaped the zombie process
            except: pass
            log_error(f"Command timed out after {timeout}s: {command}")
            return {"status": "timeout", "exit_code": -1, "stdout": "", "stderr": f"Timeout after {timeout}s", "execution_time_seconds": timeout or 0}
        except Exception as e:
            # Handle "I/O operation on closed pipe" or other pipe errors gracefully
            try:
                process.kill()
                await process.wait()
            except: pass
            log_error(f"Pipe/Process error: {str(e)}")
            return {"status": "error", "exit_code": -1, "stdout": "", "stderr": str(e), "execution_time_seconds": 0}
        
        duration = time.time() - start_time
        
        return {
            "status": "success" if process.returncode == 0 else "failed",
            "exit_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time_seconds": duration
        }
    except Exception as e:
        log_error(f"Command execution error: {str(e)}")
        return {"status": "error", "exit_code": -1, "stdout": "", "stderr": str(e), "execution_time_seconds": 0}

def save_log(path, content):
    """Save content to log file"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        logging.error(f"Failed to save log to {path}: {e}")

def execute_terraform_apply(workspace_dir, env=None):
    """Execute terraform apply with auto-approve"""
    # Use -no-color to keep logs clean
    cmd = "terraform apply -auto-approve -no-color"
    return execute_command(cmd, cwd=workspace_dir, timeout=600, env=env)

def unload_ollama_model(model_config):
    """Unload Ollama model from VRAM by setting keep_alive to 0"""
    if not model_config or 'ollama' not in model_config.get('name', '').lower():
        return
        
    try:
        base_url = model_config.get('base_url', 'http://localhost:11434/v1')
        ollama_url = base_url.replace('/v1', '/api/generate')
        
        payload = {
            "model": model_config['name'],
            "keep_alive": 0
        }
        
        logging.debug(f"Unloading Ollama model: {model_config['name']}")
        requests.post(ollama_url, json=payload, timeout=5)
    except Exception as e:
        logging.warning(f"Failed to unload Ollama model: {e}")

def capture_screenshot(task_id, model_name, screenshot_type, screenshot_dir):
    """Legacy manual screenshot capture helper"""
    # This is currently a stub for future vision-based validation
    filename = f"{task_id}_{model_name}_{screenshot_type}_{int(time.time())}.png"
    filepath = os.path.join(screenshot_dir, filename)
    # real capture logic would go here
    return filepath
