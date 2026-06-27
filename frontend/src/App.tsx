import { useEffect, useState } from "react";
import Spinner from "@cloudscape-design/components/spinner";
import Alert from "@cloudscape-design/components/alert";
import { ScanResult } from "./types";
import ScanHeader from "./components/ScanHeader";
import PicksTable from "./components/PicksTable";

export default function App() {
  const [data, setData] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    fetch(`${base}/api/scan`)
      .then((r) => {
        if (!r.ok) throw new Error(`Scan failed (HTTP ${r.status})`);
        return r.json() as Promise<ScanResult>;
      })
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [base]);

  if (error) return <Alert type="error" header="Scan error">{error}</Alert>;
  if (!data) return <Spinner size="large" />;

  return (
    <>
      <ScanHeader timestamp={data.scan_timestamp} />
      <PicksTable picks={data.picks} />
    </>
  );
}
