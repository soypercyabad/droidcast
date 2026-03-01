"""
tests/test_tools.py — Tests unitarios para el proyecto
Ejecutar: python -m pytest tests/test_tools.py -v
"""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Agregar el directorio raíz al path para importar app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestValidation(unittest.TestCase):
    """Tests de validación de entrada."""

    def test_validate_ip_valid(self):
        from app.core.adb import validate_ip
        self.assertTrue(validate_ip("192.168.1.100"))
        self.assertTrue(validate_ip("10.0.0.1"))
        self.assertTrue(validate_ip("255.255.255.255"))
        self.assertTrue(validate_ip("0.0.0.0"))

    def test_validate_ip_invalid(self):
        from app.core.adb import validate_ip
        self.assertFalse(validate_ip(""))
        self.assertFalse(validate_ip("192.168.1"))
        self.assertFalse(validate_ip("192.168.1.300"))
        self.assertFalse(validate_ip("abc.def.ghi.jkl"))
        self.assertFalse(validate_ip("192.168.1.100.5"))
        self.assertFalse(validate_ip(None))

    def test_validate_port_valid(self):
        from app.core.adb import validate_port
        self.assertTrue(validate_port("5555"))
        self.assertTrue(validate_port("1"))
        self.assertTrue(validate_port("65535"))
        self.assertTrue(validate_port("8080"))

    def test_validate_port_invalid(self):
        from app.core.adb import validate_port
        self.assertFalse(validate_port(""))
        self.assertFalse(validate_port("0"))
        self.assertFalse(validate_port("65536"))
        self.assertFalse(validate_port("-1"))
        self.assertFalse(validate_port("abc"))
        self.assertFalse(validate_port(None))


class TestConfig(unittest.TestCase):
    """Tests del sistema de configuración JSON."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")

    def tearDown(self):
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)

    def test_save_and_load_config(self):
        from app import config as cfg
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = self.config_file
        try:
            cfg.save("/ruta/test", "192.168.1.50", "5555")
            path, ip, port = cfg.load()
            self.assertEqual(path, "/ruta/test")
            self.assertEqual(ip, "192.168.1.50")
            self.assertEqual(port, "5555")
        finally:
            cfg.CONFIG_FILE = original

    def test_load_config_no_file(self):
        from app import config as cfg
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = os.path.join(self.temp_dir, "nonexistent.json")
        try:
            path, ip, port = cfg.load()
            self.assertEqual(path, "")
            self.assertEqual(ip, "")
            self.assertEqual(port, "")
        finally:
            cfg.CONFIG_FILE = original

    def test_load_config_corrupted(self):
        from app import config as cfg
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = self.config_file
        try:
            with open(self.config_file, "w") as f:
                f.write("{{{invalid json")
            path, ip, port = cfg.load()
            self.assertEqual(path, "")
            self.assertEqual(ip, "")
            self.assertEqual(port, "")
        finally:
            cfg.CONFIG_FILE = original

    def test_config_is_json(self):
        from app import config as cfg
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = self.config_file
        try:
            cfg.save("/test", "10.0.0.1", "8080")
            with open(self.config_file, "r") as f:
                data = json.load(f)
            self.assertIsInstance(data, dict)
            self.assertIn("root_path", data)
            self.assertIn("ip", data)
            self.assertIn("port", data)
        finally:
            cfg.CONFIG_FILE = original


class TestScrcpyResolution(unittest.TestCase):
    """Tests de resolución de rutas de scrcpy."""

    def test_find_existing_scrcpy_no_folder(self):
        from app.core.scrcpy import _find_existing_scrcpy
        with patch('app.core.scrcpy.BASE_DIR', tempfile.mkdtemp()):
            self.assertIsNone(_find_existing_scrcpy())

    def test_get_adb_path_fallback(self):
        from app.core.adb import get_adb_path
        with patch('app.core.scrcpy.get_scrcpy_path', return_value=None):
            self.assertEqual(get_adb_path(), "adb")

    def test_obtener_url_network_error(self):
        import requests as req
        from app.core.scrcpy import obtener_url_ultima_version
        with patch('app.core.scrcpy.requests.get',
                   side_effect=req.exceptions.ConnectionError("sin red")):
            url, version = obtener_url_ultima_version()
            self.assertIsNone(url)
            self.assertIsNone(version)


class TestAdbCommand(unittest.TestCase):
    """Tests del helper de comandos ADB."""

    def test_run_adb_file_not_found(self):
        from app.core.adb import run_adb
        with patch('app.core.adb.get_adb_path', return_value="adb_inexistente_xyz"):
            stdout, stderr, code = run_adb(["devices"])
            self.assertEqual(code, 1)
            self.assertIn("no encontrado", stderr)

    @patch('app.core.adb.subprocess.run')
    @patch('app.core.adb.get_adb_path', return_value="adb")
    def test_run_adb_success(self, _mock_adb, mock_run):
        from app.core.adb import run_adb
        mock_run.return_value = MagicMock(
            stdout="List of devices\nABC123\tdevice\n", stderr="", returncode=0)
        stdout, stderr, code = run_adb(["devices"])
        self.assertEqual(code, 0)
        self.assertIn("device", stdout)

    @patch('app.core.adb.subprocess.run')
    @patch('app.core.adb.get_adb_path', return_value="adb")
    def test_run_adb_timeout(self, _mock_adb, mock_run):
        from app.core.adb import run_adb
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=30)
        stdout, stderr, code = run_adb(["devices"])
        self.assertEqual(code, 1)
        self.assertIn("Tiempo", stderr)


if __name__ == "__main__":
    unittest.main()
