from xdgappdirs import AppDirs


dirs = AppDirs("kvm48", "org.snh48live")
USER_CONFIG_DIR = dirs.user_config_dir
USER_DATA_DIR = dirs.user_data_dir
USER_CACHE_DIR = dirs.user_cache_dir
