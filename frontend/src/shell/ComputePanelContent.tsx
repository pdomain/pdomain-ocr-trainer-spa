import {
  ComputeTargetPanel,
  createApiDeviceConfig,
} from "@pdomain/pdomain-ui/shell";
import { useDeviceInfo } from "@pdomain/pdomain-ui/stores";

const _deviceConfig = createApiDeviceConfig();

/**
 * Compute settings panel for the utility dock.
 * Backed by GET/PUT /api/suite/device (mounted by pdomain-ops mount_routes).
 */
export function ComputePanelContent(): React.JSX.Element {
  const device = useDeviceInfo(_deviceConfig);

  if (device.loading && !device.info) {
    return <p style={{ margin: 0 }}>Checking compute devices</p>;
  }

  if (device.error && !device.info) {
    return (
      <p role="alert" style={{ margin: 0, color: "var(--color-danger)" }}>
        {device.error instanceof Error
          ? device.error.message
          : typeof device.error === "string"
            ? device.error
            : "Unknown error"}
      </p>
    );
  }

  return (
    <ComputeTargetPanel
      info={device.info}
      onSelect={(deviceId) => void device.setDevice("app", deviceId)}
      onClear={(scope) => void device.clearDevice(scope)}
      cudaDocsUrl="/docs/runbooks/cuda-setup.md"
    />
  );
}
