"""Math quality metrics."""


def moving_average(values, window):
    """Return simple moving average list for a positive window."""
    if window <= 0:
        raise ValueError("window must be > 0")
    if window > len(values):
        return []

    out = []
    for i in range(len(values) - window):
        chunk = values[i : i + window]
        out.append(sum(chunk) / window)
    return out


def detect_outliers_iqr(values):
    """Detect outliers using the IQR rule."""
    if len(values) < 4:
        return []

    data = sorted(values)
    mid = len(data) // 2
    lower = data[:mid]
    upper = data[mid:]

    q1 = lower[len(lower) // 2]
    q3 = upper[len(upper) // 2]
    iqr = q3 - q1

    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    return [x for x in values if x < low or x > high]
