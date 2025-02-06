import re
import pdfplumber
import pandas  as pd
import streamlit as st
from io import BytesIO

def Mapfre(text):
    # Extracción de datos específicos del primer PDF (Certificación)
    data = {}
    
    # Search "Names and LastName"
    names_match = re.search(r"ACCIDENTADO\s+([\w\sÁÉÍÓÚÑáéíóúñ]+)\s+IDENTIFICACIÓN DE ACCIDENTADO", text, re.DOTALL)
    data["Nombres y Apellidos"] = names_match.group(1).strip() if names_match else None
    
    # Search "ID"
    id_match = re.search(r"IDENTIFICACIÓN DE ACCIDENTADO\s*(?:C\.C\s*)?([\d\.]+)", text)
    data["Identificación"] = id_match.group(1) if id_match else None
    
    # Search "Policy Number"
    policy_match = re.search(r"p[oó]liza\s+SOAT\s+expedida\s+por\s+(?:nuestra\s+aseguradora|nuestra\s+entidad)\s+bajo\s+el\s+n[uú]mero\s+(\d+)", text, re.IGNORECASE)
    data["Numero de Poliza"] = policy_match.group(1) if policy_match else None
        
    # Search "Total Paid Value"
    total_paid_match = re.search(r"(?:VALOR\s+(?:TOTAL\s+)?PAGADO|TOTAL,?\s+PAGADO)\s+A\s+LA\s+FECHA[^\$]+\$?\s*([\d\.,]+)", text, re.IGNORECASE)
    if total_paid_match:
        valor = total_paid_match.group(1)
        data["Valor Total Pagado"] = valor
    else:
        data["Valor Total Pagado"] = None
    
    # Search "Coverage"
    coverage_match = re.search(r"TOTAL,?\s+TOPE\s+DE\s+COBERTURA\s+POR\s+GASTOS\s+MÉDICOS[^\$]+\$?\s*([\d\.,]+)", text, re.IGNORECASE)
    if coverage_match:
        cobertura = coverage_match.group(1)
        data["Cobertura"] = cobertura
    else:
        data["Cobertura"] = None
        
    return data

def previsora(text):
    # Extracción de datos específicos del segundo PDF (Report)
    data = {}
    
    # Buscar "Nombres y Apellidos"
    match_names = re.search(r"ACCIDENTADO\s+([A-Za-zÁÉÍÓÚÑáéíóúñ\s]+)\s+CC\s*(\d{7,10})\s+\d{2}-\d{2}-\d{4}\s+([A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?:\n|$)", text)
    if match_names:
        name_part1 = match_names.group(1).strip()
        name_part2 = match_names.group(3).strip()
        data["Nombres y Apellidos"] = f"{name_part1} {name_part2}"
        data["Identificación"] = match_names.group(2).strip()
    else:
        match_names = re.search(
            r"ACCIDENTADO\s+CC\s*(\d{7,10})\s+([A-Za-zÁÉÍÓÚÑáéíóúñ\s]+)\s+\d{2}-\d{2}-\d{4}", text, re.IGNORECASE
        )
        if match_names:
            data["Nombres y Apellidos"] = match_names.group(2).strip()
            data["Identificación"] = match_names.group(1).strip()
            
            
    #Search "Policy Number"
    match_poliza = re.search(r"PÓLIZA DESDE HASTA PLACA\s*(\d{16})", text)
    if match_poliza:
        data["Numero de Poliza"] = match_poliza.group(1).strip()
    
    # Buscar "Coverage"
    if "NO HA AGOTADO" in text:
        data["Cobertura"] = "NO HA AGOTADO"
    elif "HA AGOTADO" in text:
        data["Cobertura"] = "HA AGOTADO"
    else:
        data["Cobertura"] = None
    
    return data

def extract_data(text, pdf_file):
    if re.search(r"MAPFRE SEGUROS GENERALES DE COLOMBIA", text, re.IGNORECASE):
        data = Mapfre(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"PREVISORA S.A.", text, re.IGNORECASE):
        data = previsora(text)
        return {**data, "Nombre archivo": pdf_file}
    else:
        raise ValueError("No se puedo identificar nombre de SOAT")

def main():
    st.title("Procesador de PDFs SOAT")
    st.write("Sube los archivos PDF para extraer la información")
    
    # Widget para subir archivos
    uploaded_files = st.file_uploader("Sube tus archivos PDF", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        results = []
        errors = []
        
        # Barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                # Actualizar progreso
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                status_text.text(f"Procesando archivo {i+1} de {len(uploaded_files)}...")
                
                # Extraer texto del PDF
                text = ""
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                if not text.strip():
                    st.warning(f"El archivo {uploaded_file.name} no contiene texto extraible")
                    continue
                
                # Procesar el archivo
                data = extract_data(text, uploaded_file.name)
                results.append(data)
                
            except Exception as e:
                st.warning(f"Formato no reconocido en {uploaded_file.name}: {str(e)}")
                errors.append(uploaded_file.name)
            except Exception as e:
                st.error(f"Error procesando {uploaded_file.name}: {str(e)}")
                errors.append(uploaded_file.name)
        
        # Mostrar resultados
        if results:
            df = pd.DataFrame(results)
            
            # Mostrar vista previa
            st.subheader("Vista previa de los datos")
            st.dataframe(df)
            
            # Generar archivo Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Datos SOAT')
                writer.close()
            
            # Botón de descarga
            st.download_button(
                label="Descargar Excel",
                data=output.getvalue(),
                file_name="resultados_soat.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            if errors:
                st.warning(f"Errores en los archivos: {', '.join(errors)}")
            
            # Resetear progreso
            progress_bar.empty()
            status_text.text("Proceso completado exitosamente!")
            
if __name__ == "__main__":
    main()
