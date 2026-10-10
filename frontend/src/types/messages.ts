export type SlideNotes = {
  slideNumber: number;
  title: string;
  slideText: string;
  importedNotes: string;
  editedNotes: string | null;
  notes: string;
};

export type Presentation = {
  presentationId: string;
  title: string;
  sourceFilename: string;
  slideCount: number;
  currentSlide: number;
  powerpointConnected: boolean;
  slideshowState: string;
  syncMessage: string;
  slides: SlideNotes[];
};

export type ServerMessage = {
  type:
    | "presentation_connected"
    | "presentation_disconnected"
    | "presentation_changed"
    | "slide_changed"
    | "notes_updated"
    | "synchronization_status"
    | "error";
  payload: Presentation | { message?: string };
};

export type StatusResponse = {
  appName: string;
  hasPresentation: boolean;
  presentation: Presentation | null;
  sessionToken: string;
};
