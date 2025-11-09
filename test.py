from src.utils import upload_folder_to_remote_linux


def test_upload_folder_to_remote_linux():
    upload_folder_to_remote_linux("config", "/data2/hzl_workspace_for_pi/test_upload", "192.168.100.63", "tpc", "root")


if __name__ == "__main__":
    test_upload_folder_to_remote_linux()