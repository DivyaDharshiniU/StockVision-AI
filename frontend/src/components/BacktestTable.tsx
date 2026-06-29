import Table from "@cloudscape-design/components/table";
import Header from "@cloudscape-design/components/header";
import { BacktestPick } from "../types";

interface Props {
  picks: BacktestPick[];
}

function formatReturn(value: number | null): string {
  if (value === null) return "N/A";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export default function BacktestTable({ picks }: Props) {
  return (
    <Table
      header={<Header counter={`(${picks.length})`}>Backtest Picks</Header>}
      columnDefinitions={[
        { id: "rank", header: "Rank", cell: (item) => item.rank },
        { id: "symbol", header: "Symbol", cell: (item) => item.symbol },
        { id: "company", header: "Company", cell: (item) => item.company_name },
        { id: "score", header: "Score", cell: (item) => item.score },
        { id: "close", header: "Close", cell: (item) => `₹${item.close.toFixed(2)}` },
        {
          id: "return_5d",
          header: "5d Return",
          cell: (item) => formatReturn(item.forward_return_5d),
        },
        {
          id: "return_10d",
          header: "10d Return",
          cell: (item) => formatReturn(item.forward_return_10d),
        },
        {
          id: "return_20d",
          header: "20d Return",
          cell: (item) => formatReturn(item.forward_return_20d),
        },
      ]}
      items={picks}
      variant="container"
    />
  );
}
