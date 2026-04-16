import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

export interface ExportPdfOptions {
  filename?: string
  onStart?: () => void
  onComplete?: () => void
  onError?: (err: Error) => void
}

export async function exportElementToPdf(element: HTMLElement, options: ExportPdfOptions = {}) {
  const { filename = '职业生涯发展报告.pdf', onStart, onComplete, onError } = options

  try {
    onStart?.()

    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      logging: false,
    })

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF('p', 'mm', 'a4')

    const pdfWidth = pdf.internal.pageSize.getWidth()
    const pdfHeight = pdf.internal.pageSize.getHeight()
    const margin = 10

    const usableWidth = pdfWidth - margin * 2
    const usableHeight = pdfHeight - margin * 2

    const imgWidth = canvas.width
    const imgHeight = canvas.height

    const scale = usableWidth / imgWidth
    const scaledHeight = imgHeight * scale

    let heightLeft = scaledHeight
    let position = 0
    let page = 0

    while (heightLeft > 0) {
      if (page > 0) {
        pdf.addPage()
      }

      const sourceY = page * (usableHeight / scale)
      const sliceHeight = Math.min(usableHeight / scale, imgHeight - sourceY)
      const drawHeight = sliceHeight * scale

      pdf.addImage(
        imgData,
        'PNG',
        margin,
        margin - position,
        usableWidth,
        scaledHeight,
      )

      heightLeft -= usableHeight
      position += usableHeight
      page++
    }

    pdf.save(filename)
    onComplete?.()
  } catch (err) {
    const error = err instanceof Error ? err : new Error('导出 PDF 失败')
    onError?.(error)
    throw error
  }
}
