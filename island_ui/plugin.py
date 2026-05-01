from abc import ABC, abstractmethod
from typing import Optional

from island_ui.events import Event
from island_ui.session import Session


class IslandPlugin(ABC):
    """AI Island 插件接口。

    商业版功能（操作审计、目录权限控制等）通过实现此接口注入核心。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称。"""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本。"""
        ...

    def on_load(self, window: "IslandWindow") -> None:
        """插件加载时调用，传入主窗口实例。"""
        pass

    def on_event(self, event: Event) -> None:
        """事件到达时调用，用于审计等场景。"""
        pass

    def on_permission_requested(
        self, session_id: str, action: str, event: Event
    ) -> Optional[str]:
        """权限请求到达时调用，可拦截或自动处理。

        Returns:
            "allow"  — 自动允许此请求
            "deny"   — 自动拒绝此请求
            None     — 不干预，走正常流程
        """
        return None

    def on_session_started(self, session: Session) -> None:
        """新会话创建时调用。"""
        pass

    def on_session_ended(self, session: Session) -> None:
        """会话结束时调用。"""
        pass

    def on_ui_ready(self, window: "IslandWindow") -> None:
        """UI 完全就绪后调用，可在此添加自定义按钮、菜单等。"""
        pass
