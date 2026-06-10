// TypefaceKanbanPage — wraps DatasetsPage for the typeface-classification task.
//
// The route /profiles/:name/datasets/typeface-classification binds this page.
// It delegates entirely to DatasetsPage (which reads the :task param from the
// route), adding only the data-testid wrapper needed for e2e + driver tests.
//
// Deviation from plan (noted): The plan referenced a KanbanBoard thumbnailMode
// prop for classifier tasks. The installed pdomain-ui version (0.7.x) does not
// expose thumbnailMode on its KanbanBoard. We use list-mode fallback per the
// plan's fallback instruction and record this as a deviation.

import { DatasetsPage } from "./DatasetsPage";

export function TypefaceKanbanPage(): React.JSX.Element {
  // Pass overrideTask so DatasetsPage does not fall back to params.task
  // (which is undefined in a literal-segment route like
  // /profiles/:name/datasets/typeface-classification).
  return (
    <div data-testid="typeface-kanban-page">
      <DatasetsPage overrideTask="typeface-classification" />
    </div>
  );
}
