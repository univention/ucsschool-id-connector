from id_sync.plugins import hook_impl, plugin_manager
from id_sync.utils import ConsoleAndFileLogging

logger = ConsoleAndFileLogging.get_logger(__name__)


class ExamplePlugin:
    @hook_impl
    def example_func(self, arg1, arg2):
        """
        Example plugin function.

        Returns the sum of its arguments.
        """
        logger.info(
            "Running ExamplePlugin.example_func() with arg1=%r arg2=%r.", arg1, arg2
        )
        return arg1 + arg2


# register plugins
plugin_manager.register(ExamplePlugin())
