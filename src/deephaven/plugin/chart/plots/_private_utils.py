from deephaven.plugin.object import Exporter
from .DeephavenFigure import DeephavenFigure

def export_figure(exporter: Exporter, figure: DeephavenFigure) -> bytes:
    return figure.to_json(exporter).encode()


def validate_common_args(
        args: dict
) -> None:
    """
    Validate common args amongst plots

    :param args: The args to validate
    """
    if not isinstance(args["table"], Table):
        raise ValueError("Argument table is not of type Table")


def remap_scene_args(
        args: dict
) -> None:
    """
    Remap layout scenes args so that they are not converted to a list

    :param args: The args to remap
    """
    for arg in ["range_x", "range_y", "range_z", "log_x", "log_y", "log_z"]:
        args[arg + '_scene'] = args.pop(arg)