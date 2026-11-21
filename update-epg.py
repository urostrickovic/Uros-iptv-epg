
import gzip
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

TEMPLATE_FILE = "Uros.xml.gz"
OUTPUT_FILE = "Uros_test.xml.gz"

SOURCE_URLS = [
    "https://iptv-epg.org/files/epg-yerukhmxxn.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_RS1.xml.gz",
    "https://www.open-epg.com/files/serbia1.xml.gz",
    "https://www.open-epg.com/files/serbia2.xml.gz",
    "https://www.open-epg.com/files/serbia4.xml.gz",
    "https://www.open-epg.com/files/serbia5.xml.gz",
    "https://epg.serbianforum.org/losmij/epg.xml.gz",
    "https://www.open-epg.com/files/croatia.xml.gz",
    "https://www.open-epg.com/files/bosnia.xml.gz",
]

# Add ID translations here only when needed.
ID_MAP = {
    # "SOURCE_ID": "YOUR_EXISTING_ID",
}


def read_xml(data):
    # Detect gzip by its file signature, not its URL extension.
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return ET.fromstring(data)


# Load your original EPG.
with gzip.open(TEMPLATE_FILE, "rb") as f:
    root = ET.parse(f).getroot()

# Preserve the original channel definitions.
channels = {
    channel.get("id")
    for channel in root.findall("channel")
}

print(f"Original channels: {len(channels)}")

# Collect existing programmes.
programmes = {}

for prog in root.findall("programme"):
    key = (
        prog.get("channel"),
        prog.get("start"),
        prog.get("stop"),
    )
    programmes[key] = prog

# Download fresh programmes.
downloaded = 0
matched = 0
unmatched_ids = defaultdict(int)
successful_sources = 0

for url in SOURCE_URLS:
    print(f"\nDownloading: {url}")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()

        source_root = read_xml(data)
        successful_sources += 1

        for prog in source_root.findall("programme"):
            source_id = prog.get("channel")
            target_id = ID_MAP.get(source_id, source_id)

            downloaded += 1

            if target_id not in channels:
                unmatched_ids[source_id] += 1
                continue

            prog.set("channel", target_id)

            key = (
                target_id,
                prog.get("start"),
                prog.get("stop"),
            )

            # Fresh data replaces an existing entry with
            # the same channel, start time and stop time.
            programmes[key] = prog
            matched += 1

        print("Source processed successfully.")

    except Exception as error:
        print(f"ERROR: {error}")
        raise RuntimeError(
            "Update stopped. Original EPG remains untouched."
        ) from error

if successful_sources == 0:
    raise RuntimeError("No EPG sources were downloaded.")

# Rebuild the XML using the original channel definitions.
new_root = ET.Element(root.tag, root.attrib)

for channel in root.findall("channel"):
    new_root.append(channel)

for prog in programmes.values():
    new_root.append(prog)

# Save as a separate compressed test file.
tree = ET.ElementTree(new_root)

with gzip.open(OUTPUT_FILE, "wb") as f:
    tree.write(
        f,
        encoding="utf-8",
        xml_declaration=True
    )

print("\nUPDATE SUMMARY")
print(f"Preserved channels: {len(channels)}")
print(f"Downloaded programmes: {downloaded}")
print(f"Matched programmes: {matched}")
print(f"Unmatched channel IDs: {len(unmatched_ids)}")
print(f"Total programmes in test: {len(programmes)}")
print(f"Test output: {OUTPUT_FILE}")

if unmatched_ids:
    print("\nSome source channel IDs did not match:")
    for channel_id, count in list(unmatched_ids.items())[:30]:
        print(f"{channel_id}: {count}")
