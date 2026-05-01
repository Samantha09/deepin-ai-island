import importlib
import logging
from typing import List

from island_ui.plugin import IslandPlugin

logger = logging.getLogger(__name__)

# 内置商业插件入口名称
_BUILTIN_PRO_PLUGIN = "island_pro"


def load_plugins(window) -> List[IslandPlugin]:
    """加载所有可用插件并返回已加载实例列表。

    加载顺序：
    1. 尝试导入内置商业包 island_pro
    2. （后续可扩展）扫描 entry_points['island_plugins']
    """
    plugins: List[IslandPlugin] = []

    # 1. 内置商业插件
    try:
        pro_module = importlib.import_module(_BUILTIN_PRO_PLUGIN)
        pro_plugin = pro_module.create_plugin()
        if isinstance(pro_plugin, IslandPlugin):
            _init_plugin(pro_plugin, window)
            plugins.append(pro_plugin)
            logger.info("商业插件已加载: %s v%s", pro_plugin.name, pro_plugin.version)
        else:
            logger.warning("island_pro.create_plugin() 返回的不是 IslandPlugin 实例")
    except ImportError:
        logger.debug("未检测到商业插件 island_pro，以开源模式运行")
    except Exception as exc:
        logger.warning("加载商业插件失败: %s", exc)

    return plugins


def _init_plugin(plugin: IslandPlugin, window) -> None:
    try:
        plugin.on_load(window)
    except Exception as exc:
        logger.error("插件 %s on_load 失败: %s", plugin.name, exc)
