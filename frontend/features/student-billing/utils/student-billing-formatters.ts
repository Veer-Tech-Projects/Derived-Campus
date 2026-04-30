export function formatCurrencyMinor(
  amountMinor: number,
  currencyCode: string,
): string {
  const normalizedCurrency = currencyCode.trim().toUpperCase();
  const amountMajor = amountMinor / 100;

  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: normalizedCurrency,
      maximumFractionDigits: 2,
    }).format(amountMajor);
  } catch {
    return `${normalizedCurrency} ${amountMajor.toFixed(2)}`;
  }
}

export function formatCreditsLabel(value: number): string {
  if (value === 1) {
    return "1 credit";
  }

  return `${value} credits`;
}

export function formatDateTimeLabel(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

export function formatRelativeSyncLabel(value: string | null | undefined): string {
  if (!value) {
    return "Last updated just now";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Last updated just now";
  }

  return `Last updated ${formatDateTimeLabel(value)}`;
}