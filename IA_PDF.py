import re
import pdfplumber
import pandas  as pd
import streamlit as st
from io import BytesIO

identificacion = pd.read_excel("Tipo_Documentos.xlsx")
tipos_identificacion = identificacion["TipoDocumento"].tolist()

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
    total_paid_match = re.search(r"(?:TOTAL|VALOR|TOTAL,)\s+(?:LIQUIDADO|PAGADO|CANCELADO)[^$]*\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if total_paid_match:
        valor = total_paid_match.group(1)
        data["Valor Total Pagado"] = valor
    else:
        data["Valor Total Pagado"] = None
    
    # Search "Coverage"
    coverage_match = re.search(r"TOPE\s+DE\s+COBERTURA[^$]+\$\s*([\d\.,]+)", text, re.IGNORECASE)
    if coverage_match:
        cobertura = coverage_match.group(1)
        data["Cobertura"] = cobertura
    else:
        data["Cobertura"] = None
    
    valor_total = int(data["Valor Total Pagado"].replace(".", "") if data["Valor Total Pagado"] else 0)
    total_cobertura = int(data["Cobertura"].replace(".", "") if data["Cobertura"] else 0)
    if valor_total < total_cobertura:
        data["Estado Cobertura"] = "NO AGOTADO"
    else:
        data["Estado Cobertura"] = "AGOTADO"
        
    return data

def previsora(text):
    # Extracción de datos específicos del segundo PDF (Report)
    data = {}
    
    # Buscar "Nombres y Apellidos"
    match_names = re.search(r"ACCIDENTADO\s+(" + "|".join(tipos_identificacion) + r")\s*(\d{5,15})\s+([A-Za-zÁÉÍÓÚÑáéíóúñ\s]+)\s+\d{2}-\d{2}-\d{4}", text)

    if match_names:
        nombres = match_names.group(3).strip()
        tipo_doc = match_names.group(1).strip().upper()
        numero_doc = match_names.group(2).strip()
        
        data["Nombres y Apellidos"] = nombres
        data["Tipo Documento"] = tipo_doc
        data["Numero Documento"] = numero_doc
        
    else:
        data["Nombres y Apellidos"] = "No encontrado"
        data["Tipo Documento"] = "No identificado"
        data["Numero Documento"] = "No encontrado"
        
            
            
    #Search "Policy Number"
    match_poliza = re.search(r"PÓLIZA DESDE HASTA PLACA\s*(\d{13,16})", text)
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

def sura(text):
    data = {}

    #Nombres y Apellidos
    tipos_id = "|".join(map(re.escape, tipos_identificacion))
    match_names = re.compile(rf"Identificación\s+accidentado\s+.*?({tipos_id})\s+(\d+)\s+([^\d]+?)\s*\d{{2}}-\d{{2}}-\d{{4}}" ,re.DOTALL | re.IGNORECASE)
    
    match_names = match_names.search(text)
    if match_names:
        data["Nombre y Apellidos"] = match_names.group(3).strip()
        data["Tipo de documento"] = match_names.group(1)
        data["Identificación"] = match_names.group(2)
    else:
        data["Nombre y Apellidos"] = "No encontrado"
        data["Tipo de documento"] = "No identificado"
        data["Identificación"] = "No encontrado"
    
    #Numero poliza
    policy_match = re.search(r"Póliza\s+número\b.*?(\d+)", text, re.DOTALL | re.IGNORECASE)
    data["Numero de Poliza"] = policy_match.group(1) if policy_match else "No encontrado"
    
    #Valores de cobertura
    total_line_match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s+UVT\s+(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s+(\d{1,3}(?:\.\d{3})*(?:,\d+)?)", text)
    if total_line_match:
        data["Cobertura"] = total_line_match.group(2)
        data["Valor total pagado"] = total_line_match.group(3)
    else:
        data["Cobertura"] = "No encontrado"
        data["Valor total pagado"] = "No encontrado"
    
    #Estado de cobertura
    if "NO" in text and "AGOTADO" in text:
        data["Estado Cobertura"] = "NO AGOTADO"
    else:
        data["Estado Cobertura"] = "AGOTADO"
    
    return data

def hdi(text):
    data = {}
    
    # Nombres y apellidos
    match_names = re.search(r"Nombre de la víctima:\s*([A-ZÁÉÍÓÚÑ ]+)", text, re.IGNORECASE)
    data["Nombres y Apellidos"] = match_names.group(1) if match_names else "No encontrado"
    
    #Identificación
    match_id = re.search(r"Número Id víctima:\s*(\d+)", text, re.IGNORECASE)
    data["Identificacion"] = match_id.group(1) if match_id else "No encontrado"
    
    #Poliza
    policy_match = re.search(r"Póliza:\s*(\d+)", text, re.IGNORECASE)
    data["Numero Poliza"] = policy_match.group(1) if policy_match else "No encontrado"
    
    #Valor total pagado
    total_paid_match = re.search(r"Valor\s*total\s*pagado\s*:\s*\$\s*([\d.,]+)", text, re.IGNORECASE)
    data["Valor Total Pagado"] = total_paid_match.group(1) if total_paid_match else "No encontrado"
    
    return data

def indemnizaciones(text):
    data = {}
    
    #Nombres y apellidos
    name_match = re.search(r"(?:La señora|El señor)\s+([A-Za-zÁÉÍÓÚÑáéíóúñ ]+),\s+identificada con", text, re.IGNORECASE)
    data["Nombres y Apellidos"] = name_match.group(1).strip() if name_match else "No encontrado"
    
    #Identificación
    id_match= re.search(r"Cédula de\s+Ciudadanía[\s\n]*([\d.,]+)", text, re.IGNORECASE)
    data["Identificacion"] = id_match.group(1).replace(".", "") if id_match else "No encontrado"
    
    #Poliza
    policy_match = re.search(r"POLIZA SOAT No\.\s*(\d+)", text,re.IGNORECASE)
    data["Numero Poliza"] = policy_match.group(1) if policy_match else "No encontrado"
    
    #Gastos medicos
    no_present_match = re.search(r"NO HA PRESENTADO PAGOS POR CONCEPTOS DE GASTOS MEDICOS", text, re.IGNORECASE)
    data["Concepto Gastos"] = "NO HA PRESENTADO GASTOS MÉDICOS" if no_present_match else "No encontrado"

    return data

def extract_data(text, pdf_file):
    if re.search(r"MAPFRE SEGUROS GENERALES DE COLOMBIA", text, re.IGNORECASE):
        data = Mapfre(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"PREVISORA S.A.", text, re.IGNORECASE):
        data = previsora(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"SEGUROS GENERALES SURAMERICANA S.A", text, re.IGNORECASE):
        data = sura(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"HDI SEGUROS COLOMBIA", text, re.IGNORECASE):
        data = hdi(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"INDEMNIZACIONES SOAT", text, re.IGNORECASE):
        data= indemnizaciones(text)
        return {**data, "Nombre archivo":pdf_file}
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
