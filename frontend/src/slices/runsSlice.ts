import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type RunStatus = "queued" | "running" | "completed" | "failed";

export interface RunSummary {
  id: number;
  outlet: string;
  country?: string;
  created_at: string;
  status: RunStatus;
  message?: string | null;
}

interface RunsState {
  selectedRunId: number | null;
}

const initialState: RunsState = {
  selectedRunId: null,
};

const runsSlice = createSlice({
  name: "runs",
  initialState,
  reducers: {
    setSelectedRunId(state, action: PayloadAction<number | null>) {
      state.selectedRunId = action.payload;
    },
  },
});

export const { setSelectedRunId } = runsSlice.actions;
export default runsSlice.reducer;


