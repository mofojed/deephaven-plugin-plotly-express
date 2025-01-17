from collections.abc import Generator

from deephaven.table import Table
from deephaven import agg, empty_table, new_table
from deephaven.column import long_col
from deephaven.time import nanos_to_millis, diff_nanos

# Used to aggregate within histogram bins
HISTFUNC_MAP = {
    'avg': agg.avg,
    'count': agg.count_,
    'count_distinct': agg.count_distinct,
    'max': agg.max_,
    'median': agg.median,
    'min': agg.min_,
    'std': agg.std,
    'sum': agg.sum_,
    'var': agg.var
}


def preprocess_aggregate(
        table: Table,
        names: str,
        values: str
) -> Table:
    """
    Preprocess a table passed to pie or funnel_area to ensure it only has 1 row
    per name

    :param table: The table to preprocess
    :param names: The column to use for names
    :param values: The column to sum up for values
    :return: A new table that contains a single row per name and columns of
    specified names and values
    """
    return table.view([names, values]).sum_by(names)


def create_count_tables(
        table: Table,
        columns: list[str],
        range_table: Table,
        histfunc: str
) -> Generator[Table, str]:
    """
    Generate count tables per column

    :param table: The table to pull data from
    :param columns: A list of columns to create histograms over
    :param range_table: A table containing ranges to calculate the bin for each
    value in the column
    :param histfunc: The function to aggregate values within each bin
    :returns: Yields a tuple containing (a new count_table, the column name)
    """
    agg_func = HISTFUNC_MAP[histfunc]
    for column in columns:
        count_table = table.view(column) \
            .join(range_table) \
            .update_view(f"RangeIndex = Range.index({column})") \
            .where("!isNull(RangeIndex)") \
            .drop_columns("Range") \
            .agg_by([agg_func(column)], "RangeIndex")
        yield count_table, column


def create_hist_tables(
        table: Table,
        columns: str | list[str],
        nbins: int,
        range_: list[int],
        histfunc: str
) -> tuple[Table, str, list[str]]:
    """
    Create the histogram table that contains aggregated bin counts

    :param table: The table to pull data from
    :param columns: A list of columns to create histograms over
    :param nbins: The number of bins, shared between all histograms
    :param range_: The range that the bins are drawn over. If none, the range
    will be over all data
    :param histfunc: The function to aggregate values within each bin
    :return: A tuple containing (the new counts table,
    the column of the midpoint, the columns that contain counts)
    """
    columns = columns if isinstance(columns, list) else [columns]

    range_table = create_range_table(table, columns, nbins, range_)
    bin_counts = new_table([
        long_col("RangeIndex", [i for i in range(nbins)])
    ])

    count_cols = []

    for count_table, count_col in \
            create_count_tables(table, columns, range_table, histfunc):
        bin_counts = bin_counts.natural_join(count_table, on=["RangeIndex"], joins=[count_col])
        count_cols.append(count_col)

    bin_counts = bin_counts.join(range_table) \
        .update_view(["BinMin = Range.binMin(RangeIndex)",
                      "BinMax = Range.binMax(RangeIndex)",
                      "BinMid=0.5*(BinMin+BinMax)"])

    return bin_counts, "BinMid", count_cols


def get_aggs(
        base: str,
        columns: list[str],
) -> tuple[list[str], str]:
    """
    Create aggregations over all columns

    :param base: The base of the new columns that store the agg per column
    :param columns: All columns joined for the sake of taking min or max over
    the columns
    :return: A tuple containing (a list of the new columns,
    a joined string of "NewCol, NewCol2...")
    """
    return ([f"{base}{column}={column}" for column in columns],
            ', '.join([f"{base}{column}" for column in columns]))


def create_range_table(
        table: Table,
        columns: list[str],
        nbins: int,
        range_: list[int]
) -> Table:
    """
    Create a table that contains the bin ranges

    :param table: The table to pull data from
    :param columns: The column names to create the range table over
    :param nbins: The number of bins to use
    :param range_: The range that the bins are drawn over. If none, the range
    will be over all data
    :return: A new table that contains a range object in a Range column
    """
    if range_:
        range_min = range_[0]
        range_max = range_[1]
        table = empty_table(1)
    else:
        range_min = "RangeMin"
        range_max = "RangeMax"
        # need to find range across all columns
        min_aggs, min_cols = get_aggs("RangeMin", columns)
        max_aggs, max_cols = get_aggs("RangeMax", columns)
        table = table.agg_by([agg.min_(min_aggs), agg.max_(max_aggs)]) \
            .update([f"RangeMin = min({min_cols})", f"RangeMax = max({max_cols})"])

    return table.update(
        f"Range = new io.deephaven.plot.datasets.histogram."
        f"DiscretizedRangeEqual({range_min},{range_max}, "
        f"{nbins})").view("Range")


def time_length(
        start: str,
        end: str
) -> int:
    """
    Calculate the difference between the start and end times in milliseconds

    :param start: The start time
    :param end: The end time
    :return: The time in milliseconds
    """
    return nanos_to_millis(diff_nanos(start, end))


def preprocess_frequency_bar(
        table: Table,
        column: str
) -> tuple[Table, str, str]:
    """
    Preprocess frequency bar params into an appropriate table
    This just sums each value by count

    :param table: The table to pull data from
    :param column: The column that has counts applied
    :return: A tuple containing (the new table, the original column name,
    the name of the count column)
    """
    return table.view([column]).count_by("Count", by=column), column, "Count"


# todo: always modify given column names to prevent column collisions?
def preprocess_timeline(
        table: Table,
        x_start: str,
        x_end: str,
        y: str
) -> tuple[Table, str]:
    """
    Preprocess timeline params into an appropriate table
    The table should contain the Time_Diff, which is milliseconds between the
    provided x_start and x_end

    :param table: The table to pull data from
    :param x_start: The column that contains start dates
    :param x_end: The column that contains end dates
    :param y: The label for the row
    :return: A tuple containing (the new table,
    the name of the new time_diff column)
    """
    new_table = table.view([f"{x_start}",
                            f"{x_end}",
                            f"Time_Diff = time_length({x_start}, {x_end})",
                            f"{y}"])
    return new_table, "Time_Diff"


def preprocess_violin(
        table: Table,
        column: str
) -> tuple[Table, str, str]:
    """
    Preprocess the violin (or box or strip) params into an appropriate table
    For each column, the data needs to be reshaped so that there is a column
    that contains the column name, and a column that contains the value

    :param table: The table to pull data from
    :param column: The column to use for violin data
    :return: A tuple of new_table, column names, and column values
    """
    col_names, col_vals = f"{column}_names", f"{column}_vals",
    # also used for box and strip
    new_table = table.view([
        f"{col_names} = `{column}`",
        f"{col_vals} = {column}"
    ])

    return new_table, col_names, col_vals
