/**
 * Shared CV download mechanics (REQ-A6) — extracted from CvSection so the TUI
 * content-pane Enter action triggers the exact same download as the button.
 */
export async function downloadCv(cvUrl: string): Promise<void> {
  try {
    const response = await fetch(cvUrl);
    if (!response.ok) throw new Error('Download failed');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Johny_A._Pedraza_Romero_CV.pdf';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch {
    window.open(cvUrl, '_blank');
  }
}
