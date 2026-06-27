import { LineChart, Line, ResponsiveContainer } from "recharts";

interface Props {
  prices: number[];
}

export default function Sparkline({ prices }: Props) {
  const color =
    prices[prices.length - 1] >= prices[0] ? "#2ea44f" : "#d73a49";
  const data = prices.map((v, i) => ({ i, v }));
  return (
    <ResponsiveContainer width={100} height={40}>
      <LineChart data={data}>
        <Line
          type="monotone"
          dataKey="v"
          stroke={color}
          dot={false}
          strokeWidth={1.5}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
