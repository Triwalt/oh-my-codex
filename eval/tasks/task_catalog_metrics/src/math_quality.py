"""Catalog metric helpers."""


def trimmed_mean(values, trim_ratio):
    """Return the trimmed mean for a sorted ratio between 0 and 0.49."""
    if not 0 <= trim_ratio < 0.5:
        raise ValueError("trim_ratio must be between 0 and 0.5")
    if not values:
        raise ValueError("values must not be empty")

    data = sorted(values)
    cut = int(len(data) * trim_ratio)
    trimmed = data[cut : len(data) - cut]
    return sum(trimmed) / len(trimmed)


def moving_range(values):
    """Return the absolute range between adjacent values."""
    if len(values) < 2:
        return []

    out = []
    for i in range(len(values) - 2):
        out.append(abs(values[i + 1] - values[i]))
    return out
