import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import ColumnLayout from "@cloudscape-design/components/column-layout";
import Box from "@cloudscape-design/components/box";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import { PrecisionRecall } from "../types";

interface Props {
  precisionRecall: PrecisionRecall;
}

function formatMetric(value: number | null): string {
  if (value === null) return "N/A";
  return `${value.toFixed(2)}%`;
}

function getStatus(value: number | null): "success" | "warning" | "error" | "info" {
  if (value === null) return "info";
  if (value >= 70) return "success";
  if (value >= 40) return "warning";
  return "error";
}

export default function PrecisionRecallPanel({ precisionRecall }: Props) {
  return (
    <Container header={<Header variant="h2">Model Accuracy</Header>}>
      <ColumnLayout columns={3}>
        <div>
          <Box variant="h3">5-day</Box>
          <Box variant="awsui-key-label">Precision</Box>
          <StatusIndicator type={getStatus(precisionRecall.precision_5d)}>
            {formatMetric(precisionRecall.precision_5d)}
          </StatusIndicator>
          <Box variant="awsui-key-label">Recall</Box>
          <StatusIndicator type={getStatus(precisionRecall.recall_5d)}>
            {formatMetric(precisionRecall.recall_5d)}
          </StatusIndicator>
        </div>
        <div>
          <Box variant="h3">10-day</Box>
          <Box variant="awsui-key-label">Precision</Box>
          <StatusIndicator type={getStatus(precisionRecall.precision_10d)}>
            {formatMetric(precisionRecall.precision_10d)}
          </StatusIndicator>
          <Box variant="awsui-key-label">Recall</Box>
          <StatusIndicator type={getStatus(precisionRecall.recall_10d)}>
            {formatMetric(precisionRecall.recall_10d)}
          </StatusIndicator>
        </div>
        <div>
          <Box variant="h3">20-day</Box>
          <Box variant="awsui-key-label">Precision</Box>
          <StatusIndicator type={getStatus(precisionRecall.precision_20d)}>
            {formatMetric(precisionRecall.precision_20d)}
          </StatusIndicator>
          <Box variant="awsui-key-label">Recall</Box>
          <StatusIndicator type={getStatus(precisionRecall.recall_20d)}>
            {formatMetric(precisionRecall.recall_20d)}
          </StatusIndicator>
        </div>
      </ColumnLayout>
    </Container>
  );
}
