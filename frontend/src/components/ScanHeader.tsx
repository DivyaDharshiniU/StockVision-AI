import Header from "@cloudscape-design/components/header";

interface Props {
  timestamp: string;
}

export default function ScanHeader({ timestamp }: Props) {
  const formatted = new Date(timestamp).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    dateStyle: "medium",
    timeStyle: "short",
  });
  return (
    <Header variant="h1" description={`Last scanned: ${formatted} IST`}>
      StockVision AI
    </Header>
  );
}
