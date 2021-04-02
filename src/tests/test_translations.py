import pathlib
import sys
from typing import Tuple, List, Dict

import string
from babel.messages.pofile import read_po
from babel.messages import catalog

SRC_DIRECTORY = pathlib.Path(__file__).parent.parent
print(f"Detected src directory: {SRC_DIRECTORY}")

LOCALES_DIRECTORY = SRC_DIRECTORY / "locales"
print(f"Detected locales directory: {LOCALES_DIRECTORY}")

INFO = "▶️"
WARNING = "⚠️"
ERROR = "🚨"

formatter = string.Formatter()


def extract_keys(format_string) -> List[str]:
    keys = []
    for _, field_name, _, _ in formatter.parse(format_string):
        if field_name:
            keys.append(field_name)

    return keys


def check_po_file(file: pathlib.Path) -> Tuple[bool, List[str]]:
    result, messages = True, []
    with open(file, "r") as f:
        messages_catalog: catalog.Catalog = read_po(f, ignore_obsolete=True)

    untranslated_messages = 0

    for po_message in messages_catalog:
        po_message: catalog.Message

        maybe_tuple_message_id = po_message.id
        maybe_tuple_message_string = po_message.string

        if not isinstance(maybe_tuple_message_id, tuple):
            maybe_tuple_message_id = (maybe_tuple_message_id, )
            maybe_tuple_message_string = (maybe_tuple_message_string, )

        for message_id, message_string in zip(maybe_tuple_message_id, maybe_tuple_message_string):
            html_detects = ["&gt;", "&lt;", "&nbsp;"]
            if not len(message_string):
                # Not bad but still good to show
                # messages.append(f"{INFO} `{message_id}` is untranslated")
                untranslated_messages += 1
                break

            for html_detect in html_detects:
                if html_detect in message_string and not html_detect in message_id:
                    messages.append(f"{WARNING} Detected HTML tag {html_detect}:\n"
                                    f"ID_: {message_id}\n"
                                    f"STR: {message_string}")

            message_id_keys = extract_keys(message_id)
            try:
                message_string_keys = extract_keys(message_string)
            except ValueError as e:
                messages.append(f"{ERROR} Bad f-string formatting:\n"
                                f"ID_: {message_id_keys} ({message_id})\n"
                                f"STR: {message_string} ({e})")
                result = False
            else:
                if len(message_id_keys) != len(message_string_keys):
                    messages.append(f"{ERROR} Mistranslated (missing f-keys):\n"
                                    f"ID_: {message_id_keys} ({message_id})\n"
                                    f"STR: {message_string_keys} ({message_string})")
                    result = False
                elif sorted(message_id_keys) != sorted(message_string_keys):
                    messages.append(f"{ERROR} Probably mistranslated (different f-keys):\n"
                                    f"ID_: {message_id_keys} ({message_id})\n"
                                    f"STR: {message_string_keys} ({message_string})")
                    result = False


    messages.append(f"{INFO} {untranslated_messages} untranslated messages")
    return result, messages


def main():
    failed_files: Dict[pathlib.Path, List[str]] = {}
    for po_file in LOCALES_DIRECTORY.rglob("*.po"):
        result, messages = check_po_file(po_file)
        if result:
            print(f"✅ {po_file}")
        else:
            print(f"❌ {po_file}")
            failed_files[po_file] = messages

    if failed_files:
        print("======================")
        print(f"{len(failed_files)} files failed.")
        for failed_po_file, messages in failed_files.items():
            print(f"❌ {failed_po_file}")
            for message in messages:
                print(f"\t -> {message}")
            print("\n-----\n")
    else:
        print(f"✅ All is good !")
    sys.exit(len(failed_files))


if __name__ == '__main__':
    main()

