import type { components } from "./contracts";
export type Meeting = components["schemas"]["Meeting"];
export type Profile = components["schemas"]["Profile"];
export type Preferences = components["schemas"]["Preferences"];
export type Participant = components["schemas"]["Participant"];
export type Tag = components["schemas"]["Tag"];
export type Task = components["schemas"]["Task"];
export type Activity = components["schemas"]["Activity"];
export type Page<T> = Omit<components["schemas"]["Page_Meeting_"], "items"> & {
  items: T[];
};
