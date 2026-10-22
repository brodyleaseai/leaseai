"""Download Phase 4 Streamlit pages using the GitHub emoji filenames."""
import os
import urllib.request

BASE = "https://raw.githubusercontent.com/brodyleaseai/leaseai/main"
FILES = [
    ("pages/15_%F0%9F%92%B3_Billing.py", "pages/15_\U0001f4b3_Billing.py"),
    ("pages/1_%F0%9F%93%A4_Upload_Lease.py", "pages/1_\U0001f4e4_Upload_Lease.py"),
    ("pages/4_%F0%9F%93%8A_Admin_Dashboard.py", "pages/4_\U0001f4ca_Admin_Dashboard.py"),
    ("pages/7_%F0%9F%91%A5_Client_Portal.py", "pages/7_\U0001f465_Client_Portal.py"),
    ("pages/9_%F0%9F%93%A6_Bulk_Upload.py", "pages/9_\U0001f4e6_Bulk_Upload.py"),
]


def main():
    os.makedirs("pages", exist_ok=True)
    for url_path, dest in FILES:
        print(f"Downloading {dest} ...", end=" ")
        urllib.request.urlretrieve(f"{BASE}/{url_path}", dest)
        print("OK")
    print("All Phase 4 pages downloaded.")


if __name__ == "__main__":
    main()
