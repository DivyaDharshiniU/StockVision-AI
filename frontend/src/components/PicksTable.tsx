import { useState } from "react";
import Table, {
  TableProps,
} from "@cloudscape-design/components/table";
import { TopPick } from "../types";
import Sparkline from "./Sparkline";

interface Props {
  picks: TopPick[];
}

type SortKey = keyof Omit<TopPick, "price_history_30d">;

const columnDefinitions: TableProps.ColumnDefinition<TopPick>[] = [
  {
    id: "rank",
    header: "Rank",
    cell: (p) => p.rank,
    sortingField: "rank",
  },
  {
    id: "symbol",
    header: "Symbol",
    cell: (p) => p.symbol,
    sortingField: "symbol",
  },
  {
    id: "company_name",
    header: "Company",
    cell: (p) => p.company_name,
    sortingField: "company_name",
  },
  {
    id: "score",
    header: "Score",
    cell: (p) => p.score,
    sortingField: "score",
  },
  {
    id: "close",
    header: "Close (₹)",
    cell: (p) => `₹${p.close.toFixed(2)}`,
    sortingField: "close",
  },
  {
    id: "sma50",
    header: "SMA50",
    cell: (p) => p.sma50.toFixed(2),
    sortingField: "sma50",
  },
  {
    id: "sma200",
    header: "SMA200",
    cell: (p) => p.sma200.toFixed(2),
    sortingField: "sma200",
  },
  {
    id: "volume_ratio",
    header: "Volume Ratio",
    cell: (p) => p.volume_ratio.toFixed(2),
    sortingField: "volume_ratio",
  },
  {
    id: "pct_from_52w_high",
    header: "% from 52W High",
    cell: (p) => `${p.pct_from_52w_high.toFixed(2)}%`,
    sortingField: "pct_from_52w_high",
  },
  {
    id: "trend",
    header: "Trend",
    cell: (p) => <Sparkline prices={p.price_history_30d} />,
  },
];

export default function PicksTable({ picks }: Props) {
  const [sortingColumn, setSortingColumn] = useState<
    TableProps.SortingColumn<TopPick> | undefined
  >(undefined);
  const [isDescending, setIsDescending] = useState(false);

  const sortedPicks = [...picks].sort((a, b) => {
    if (!sortingColumn?.sortingField) return 0;
    const key = sortingColumn.sortingField as SortKey;
    const aVal = a[key];
    const bVal = b[key];
    if (aVal < bVal) return isDescending ? 1 : -1;
    if (aVal > bVal) return isDescending ? -1 : 1;
    return 0;
  });

  return (
    <Table
      items={sortedPicks}
      columnDefinitions={columnDefinitions}
      sortingColumn={sortingColumn}
      sortingDescending={isDescending}
      onSortingChange={({ detail }) => {
        setSortingColumn(detail.sortingColumn);
        setIsDescending(detail.isDescending ?? false);
      }}
    />
  );
}
