from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from urllib.parse import urlparse
from typing import Union
from pathlib import Path


def download_file(url: str, download_path: Union[Path, str]):
    url = urlparse(url)
    storage_account_name = url.netloc.split(".")[0]
    container_name = [part for part in url.path.split("/") if part][0]
    blob_name = "/".join([part for part in url.path.split("/") if part][1:])
    cred = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net",
        credential=cred,
    )
    container_client = blob_service_client.get_container_client(container_name)
    with open(download_path, "wb") as download_file:
        download_file.write(container_client.download_blob(blob_name).readall())
