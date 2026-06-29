import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { BacktestPick, BenchmarkReturns } from "../types";

interface Props {
  picks: BacktestPick[];
  benchmarkReturns: BenchmarkReturns;
}

export default function BacktestChart({ picks, benchmarkReturns }: Props) {
  const avgReturn = (values: (number | null)[]): number | null => {
    const valid = values.filter((v): v is number => v !== null);
    if (valid.length === 0) return null;
    return parseFloat(
      (valid.reduce((a, b) => a + b, 0) / valid.length).toFixed(2)
    );
  };

  const data = [
    {
      window: "5-day",
      avgPickReturn: avgReturn(picks.map((p) => p.forward_return_5d)),
      benchmark: benchmarkReturns.return_5d,
    },
    {
      window: "10-day",
      avgPickReturn: avgReturn(picks.map((p) => p.forward_return_10d)),
      benchmark: benchmarkReturns.return_10d,
    },
    {
      window: "20-day",
      avgPickReturn: avgReturn(picks.map((p) => p.forward_return_20d)),
      benchmark: benchmarkReturns.return_20d,
    },
  ];

  return (
    <Container header={<Header variant="h2">Returns Comparison</Header>}>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="window" />
          <YAxis unit="%" />
          <Tooltip formatter={(value: number) => `${value}%`} />
          <Legend />
          <Bar dataKey="avgPickReturn" name="Avg Pick Return" fill="#0972d3" />
          <Bar dataKey="benchmark" name="Benchmark (Nifty)" fill="#ec7211" />
        </BarChart>
      </ResponsiveContainer>
    </Container>
  );
}
