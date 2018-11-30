import os

from xdgappdirs import AppDirs


dirs = AppDirs("kvm48", "org.snh48live", roaming=True)
USER_CONFIG_DIR = dirs.user_config_dir
USER_DATA_DIR = dirs.user_data_dir
USER_CACHE_DIR = dirs.user_cache_dir

V10LEGACY_USER_CONFIG_DIR = (
    AppDirs("kvm48", "org.snh48live", roaming=False).user_config_dir
    if os.name == "nt"
    else None
)
