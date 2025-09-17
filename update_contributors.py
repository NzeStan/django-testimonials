import requests
import re
import os

# ==== CONFIGURATION ====
GITHUB_USERNAME = "NzeStan" 
REPOSITORY_NAME = "django-testimonials" 

# Auto-detect README.md file (searches repo for it)
def find_readme():
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.lower() == "readme.md":
                return os.path.join(root, file)
    return None

README_FILE = find_readme()
if not README_FILE:
    print("❌ Could not find README.md in this project.")
    exit()

# GitHub API URL for contributors
url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPOSITORY_NAME}/contributors"

# Fetch contributors
print("🔄 Fetching contributors from GitHub...")
response = requests.get(url)
if response.status_code != 200:
    print(f"❌ Error fetching contributors: {response.status_code}")
    print(response.json())
    exit()

contributors = response.json()

# Generate Markdown table
table_md = "## Contributors\n\nThanks to these amazing people for contributing 💙\n\n"
table_md += f'<a href="https://github.com/{GITHUB_USERNAME}/{REPOSITORY_NAME}/graphs/contributors">\n'
table_md += f'  <img src="https://contrib.rocks/image?repo={GITHUB_USERNAME}/{REPOSITORY_NAME}" />\n</a>\n\n'
table_md += "<br>\n\n<table>\n  <tr>\n"

for i, contributor in enumerate(contributors):
    username = contributor["login"]
    avatar_url = contributor["avatar_url"]
    profile_url = contributor["html_url"]

    table_md += f'''    <td align="center">
      <a href="{profile_url}">
        <img src="{avatar_url}" width="100px;" alt="{username}"/>
        <br />
        <sub><b>{username}</b></sub>
      </a>
    </td>\n'''

    # Wrap after 6 contributors
    if (i + 1) % 6 == 0:
        table_md += "  </tr>\n  <tr>\n"

table_md += "  </tr>\n</table>\n\n"
table_md += f"Made with [contrib.rocks](https://contrib.rocks)."

# Read current README
with open(README_FILE, "r", encoding="utf-8") as f:
    readme_content = f.read()

# Replace or insert section
pattern = re.compile(r"## Contributors.*?(?=\n##|\Z)", re.S)
if re.search(pattern, readme_content):
    new_content = re.sub(pattern, table_md, readme_content)
    print(f"✏️ Updating existing Contributors section in {README_FILE}...")
else:
    new_content = readme_content.strip() + "\n\n" + table_md
    print(f"➕ Adding Contributors section to {README_FILE}...")

# Write updated README
with open(README_FILE, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"✅ Contributors section updated in {README_FILE}")
