import { configureStore } from "@reduxjs/toolkit";
import runsReducer from "./slices/runsSlice";

export const store = configureStore({
  reducer: {
    runs: runsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;


