import pathlib
import sys
from typing import Tuple, List, Dict

import discord
import os
import string

from babel.messages.pofile import read_po
from babel.messages import catalog

SRC_DIRECTORY = pathlib.Path(__file__).parent.parent
print(f"Detected src directory: {SRC_DIRECTORY}")

LOCALES_DIRECTORY = SRC_DIRECTORY / "locales"
print(f"Detected locales directory: {LOCALES_DIRECTORY}")

INFO = "▶️"
INFO_COLOR = discord.Color.dark_gray()
WARNING = "⚠️"
WARNING_COLOR = discord.Color.orange()
ERROR = "🚨"
ERROR_COLOR = discord.Color.red()

formatter = string.Formatter()


def extract_keys(format_string) -> List[str]:
    keys = []
    for _, field_name, _, _ in formatter.parse(format_string):
        if field_name:
            keys.append(field_name)

    return keys


def check_po_file(file: pathlib.Path) -> Tuple[bool, List[str], List[discord.Embed]]:
    result, messages, embeds = True, [], []
    with open(file, "r") as f:
        messages_catalog: catalog.Catalog = read_po(f, ignore_obsolete=True)

    lang_name = str(file.parent.parent.name)

    untranslated_messages = 0

    for po_message in messages_catalog:
        po_message: catalog.Message

        maybe_tuple_message_id = po_message.id
        maybe_tuple_message_string = po_message.string

        if not isinstance(maybe_tuple_message_id, tuple):
            maybe_tuple_message_id = (maybe_tuple_message_id,)
            maybe_tuple_message_string = (maybe_tuple_message_string,)

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

                    e = discord.Embed(color=WARNING_COLOR,
                                      title=lang_name,
                                      description=f"HTML tag detected: {html_detect}")
                    e.add_field(name="English message", value=message_id[:250], inline=False)
                    e.add_field(name="Translated message", value=message_string[:250], inline=False)
                    embeds.append(e)

            message_id_keys = extract_keys(message_id)
            try:
                message_string_keys = extract_keys(message_string)
            except ValueError as e:
                messages.append(f"{ERROR} Bad f-string formatting:\n"
                                f"ID_: {message_id_keys} ({message_id})\n"
                                f"STR: {message_string} ({e})")

                em = discord.Embed(color=ERROR_COLOR,
                                   title=lang_name,
                                   description=f"Bad f-string formatting")

                em.add_field(name="Keys in english", value=str(message_id_keys), inline=False)
                em.add_field(name="Error", value=str(e), inline=False)

                em.add_field(name="English message", value=message_id[:250], inline=False)
                em.add_field(name="Translated message", value=message_string[:250], inline=False)
                embeds.append(em)

                result = False
            else:
                e = discord.Embed(color=ERROR_COLOR,
                                  title=lang_name,)

                e.add_field(name="Keys in english", value=str(message_id_keys), inline=False)
                e.add_field(name="Keys in translation", value=str(message_string_keys), inline=False)

                e.add_field(name="English message", value=message_id[:250], inline=False)
                e.add_field(name="Translated message", value=message_string[:250], inline=False)

                if len(message_id_keys) != len(message_string_keys):
                    messages.append(f"{ERROR} Mistranslated (missing f-keys):\n"
                                    f"ID_: {message_id_keys} ({message_id})\n"
                                    f"STR: {message_string_keys} ({message_string})")

                    e.description = f"Mistranslated (missing f-keys)"
                    embeds.append(e)

                    result = False
                elif sorted(message_id_keys) != sorted(message_string_keys):
                    messages.append(f"{ERROR} Probably mistranslated (different f-keys):\n"
                                    f"ID_: {message_id_keys} ({message_id})\n"
                                    f"STR: {message_string_keys} ({message_string})")

                    e.description = f"Probably mistranslated (different f-keys)"
                    embeds.append(e)

                    result = False

    messages.append(f"{INFO} {untranslated_messages} untranslated messages")

    return result, messages, embeds


def main():
    webhook_url = os.environ.get("L10N_WEBHOOK_URL", None)
    webhook = None

    if webhook_url:
        webhook = discord.SyncWebhook.from_url(url=webhook_url)
        print(f"Detected webhook OS var... Logging to #l10n")
    else:
        print(f"Webhook OS var not detected... Are we in a PR ?")

    failed_files: Dict[pathlib.Path, List[str]] = {}
    failed_files_embeds: Dict[pathlib.Path, List[discord.Embed]] = {}
    for po_file in LOCALES_DIRECTORY.rglob("*.po"):
        print(f"➡️ {po_file}")
        result, messages, embeds = check_po_file(po_file)
        if result:
            print(f"✅ {po_file}")
        else:
            print(f"❌ {po_file}")
            failed_files[po_file] = messages
            failed_files_embeds[po_file] = embeds

    if failed_files:
        print("======================")
        print(f"{len(failed_files)} files failed.")
        for failed_po_file, messages in failed_files.items():
            print(f"❌ {failed_po_file}")
            for message in messages:
                print(f"\t -> {message}")
            print("\n-----\n")

    if failed_files_embeds and webhook:
        for failed_po_file, embeds in failed_files_embeds.items():
            for embed in embeds:
                webhook.send(embed=embed)
    else:
        print(f"✅ All is good !")
    sys.exit(len(failed_files))


if __name__ == '__main__':
    main()
