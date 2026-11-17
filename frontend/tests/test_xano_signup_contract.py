import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIGNUP_PATH = PROJECT_ROOT / "xano" / "api" / "authentication" / "auth" / "signup_POST.xs"


class XanoSignupContractTests(unittest.TestCase):
    def test_signup_saves_raw_password_once_in_sensitive_input(self):
        signup_source = SIGNUP_PATH.read_text(encoding="utf-8")
        input_block = signup_source.split("input {", 1)[1].split("\n  }", 1)[0]

        self.assertRegex(
            input_block,
            re.compile(
                r"text owner_password\s*"
                r"\{\s*sensitive\s*=\s*true\s*\}",
                re.DOTALL,
            ),
        )
        self.assertNotRegex(input_block, r"minAlpha|minDigit")
        self.assertRegex(
            signup_source,
            r"\(\$input\.owner_password\|strlen\) >= 8",
        )
        self.assertIn(
            '$input.owner_password|regex_replace:"[A-Za-z]":""',
            signup_source,
        )
        self.assertIn(
            '$input.owner_password|regex_replace:"[0-9]":""',
            signup_source,
        )
        self.assertRegex(signup_source, r"password:\s*\$input\.owner_password")

    def test_signup_assigns_a_unique_nonlegacy_migration_key(self):
        signup_source = SIGNUP_PATH.read_text(encoding="utf-8")
        barbershop_insert = signup_source.split("db.add barbershop {", 1)[1].split(
            "} as $barbershop", 1
        )[0]

        self.assertIn("security.create_uuid as $barbershop_migration_key", signup_source)
        self.assertRegex(
            barbershop_insert,
            r"migration_key:\s*\$barbershop_migration_key",
        )


if __name__ == "__main__":
    unittest.main()
