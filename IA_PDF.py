import re
import pdfplumber
import pandas  as pd
import streamlit as st
from io import BytesIO

identificacion = pd.read_excel("Tipo_Documentos.xlsx")
tipos_identificacion = identificacion["TipoDocumento"].tolist()

# Character identification of different SOAT Entities 

def Mapfre(text):
    # Extraction of specific data from the first PDF (Certification)
    data = {}
    
    # Search "Names and LastName"
    names_match = re.search(r"ACCIDENTADO\s+([\w\sÁÉÍÓÚÑáéíóúñ]+)\s+IDENTIFICACIÓN DE ACCIDENTADO", text, re.DOTALL)
    data["Nombres y Apellidos"] = names_match.group(1).strip() if names_match else None
    
    # Search "ID"
    id_match = re.search(r"IDENTIFICACIÓN DE ACCIDENTADO\s*(?:C\.?C\s*)?([\d\.]+)", text)
    data["Identificación"] = id_match.group(1) if id_match else None
        
    # Search "Policy Number"
    policy_match = re.search(r"p[oó]liza\s+SOAT\s+expedida\s+por\s+(?:nuestra\s+aseguradora|nuestra\s+entidad)\s+bajo\s+el\s+n[uú]mero\s+(\d+)", text, re.IGNORECASE)
    data["Numero de Poliza"] = policy_match.group(1) if policy_match else None
        
    # Search "Total Paid Value"
    total_paid_match = re.search(r"(?:TOTAL|VALOR|TOTAL,)\s+(?:LIQUIDADO|PAGADO|CANCELADO|RECLAMADO)[^$]*\$\s*([\d\.,]+)", text, re.IGNORECASE)
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
    
    date_match = re.search(r"FECHA DEL ACCIDENTE\s+(\d{2}/\d{2}/\d{4})", text)
    data["Fecha Siniestro"] = date_match.group(1).strip() if date_match else "No encontrado"
        
    return data

def previsora(text):
    # Extraction of specific data from the second PDF (Report)
    data = {}
    
    match_new_id = re.search(r"(AS|ERI|[A-Z]{2})\s*(\d+[A-Z]\d+|\d{8}[A-Z]{2})", text)
    if match_new_id:
        data["Tipo Documento"] = match_new_id.group(1).strip().upper()
        data["Numero de Documento"] = match_new_id.group(2).strip()
    else:
    # Search "Name and Last Name" new format
        match_names_old = re.search(r"\b(" + "|".join(tipos_identificacion) + r")\s+(\d{5,15})\s+([A-Za-zÁÉÍÓÚÑáéíóúñ0-9\s]+?)\s+\d{2}-\d{2}-\d{4}", text, re.DOTALL)
        
        if match_names_old:
            data["Nombres y Apellidos"] = match_names_old.group(3).strip()
            data["Tipo Documento"] = match_names_old.group(1).strip().upper()
            data["Numero de Documento"] = match_names_old.group(2).strip()
        else:
            match_ven = re.search(r"ACCIDENTADO.*?(MS|AS|CC|TI)\s+(VEN\d+)\s+([A-ZÁÉÍÓÚÑ\s]+?)\s+\d{2}-\d{2}-\d{4}", text, re.DOTALL) 
            if match_ven:
                data["Nombres y Apellidos"] = match_ven.group(3).strip()
                data["Numero de Documento"] = match_ven.group(2).strip()
                
                doc_match = re.search(
                    r"\b(" + "|".join(map(re.escape, tipos_identificacion)) + r")\b",
                    match_ven.group(0)
                )
                # Puts the type of document concerned
                if doc_match:
                    data["Tipo Documento"] = doc_match.group(1).strip().upper()
                else:
                    data["Tipo Documento"] = "No encontrado"
            else:
                tipos_regex= "|".join(map(re.escape, tipos_identificacion))
                match_split_n = re.search(
                    r"ACCIDENTADO(?:\s+VÍCTIMA\s+SINIESTRO)?\s*\n"
                    r"(?P<nombre1>[A-ZÁÉÍÓÚÑ\s]+)"                      # Primera línea del nombre
                    r"(?:\n(?P<nombre2>(?!(" + tipos_regex + r")\b)[A-ZÁÉÍÓÚÑ\s]+))?"  # Segunda línea opcional del nombre
                    r"\n\s*(?P<tipo>(" + tipos_regex + r"))\s*(?P<num>\d{5,15})"  # Línea con tipo y número
                    r"(?:\s*\n\s*(?P<nombre3>[A-ZÁÉÍÓÚÑ\s]+))?",
                    text,
                    re.DOTALL
                )
                if match_split_n:
                    nombre = match_split_n.group("nombre1").strip()
                    if match_split_n.group("nombre2"):
                            nombre += " " + match_split_n.group("nombre2").strip()
                    if match_split_n.group("nombre3"):
                        nombre += " " + match_split_n.group("nombre3").strip()
                    data["Nombres y Apellidos"] = nombre
                    data["Tipo Documento"] = match_split_n.group("tipo").strip().upper()
                    data["Numero de Documento"] = match_split_n.group("num").strip()
                else:
                    data.update({
                        "Nombres y Apellidos": "No encontrado",
                        "Tipo Documento": "No encontrado",
                        "Numero de Documento": "No encontrado"
                    })
    match_policy = re.search(
        r"PÓLIZA DESDE HASTA PLACA\s*(\d{13,16})", 
        text
    )
    
    if match_policy:
        data["Numero de Poliza"] = match_policy.group(1).strip()
    else:
        data["Numero de Poliza"] = "No encontrado"
    
    if "NO HA AGOTADO" in text:
        data["Cobertura"] = "NO HA AGOTADO"
    elif "HA AGOTADO" in text:
        data["Cobertura"] = "HA AGOTADO"
    else:
        data["Cobertura"] = "No encontrado"
    
    #Search "Accident Date"
    date_match = re.search("(\d{2}-\d{2}-\d{4})(?:\s*\$|$)", text, re.MULTILINE)
    data["Fecha Siniestro"] = date_match.group(1).strip() if date_match else "No encontrado"
    
    return data

def sura(text):
    data = {}

    #Search Names and Lastnames
    tipos_id = "|".join(map(re.escape, tipos_identificacion))
    match_names = re.compile(rf"(?:Identificación\s+accidentado\s+.*?)?({tipos_id})\s+(\d+)\s+([^\d]+?)\s*\d{{2}}-\d{{2}}-\d{{4}}" ,re.DOTALL | re.IGNORECASE)
    
    match_names = match_names.search(text)
    if match_names:
        data["Nombres y Apellidos"] = match_names.group(3).strip()
        data["Tipo de documento"] = match_names.group(1)
        data["Identificación"] = match_names.group(2)
    else:
        data["Nombre y Apellidos"] = "No encontrado"
        data["Tipo de documento"] = "No identificado"
        data["Identificación"] = "No encontrado"
    
    #Search a Number Policy
    policy_match = re.search(r"(\d{8,12})", text)
    data["Numero de Poliza"] = policy_match.group() if policy_match else "No encontrado"
    
    #Search a value coverage
    total_line_match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s+UVT\s+(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s+(\d{1,3}(?:\.\d{3})*(?:,\d+)?)", text)
    if total_line_match:
        data["Cobertura"] = total_line_match.group(2)
        data["Valor total pagado"] = total_line_match.group(3)
    else:
        data["Cobertura"] = "No encontrado"
        data["Valor total pagado"] = "No encontrado"
    
    #Search Coverage Status
    if "NO" in text and "AGOTADO" in text:
        data["Estado Cobertura"] = "NO AGOTADO"
    else:
        data["Estado Cobertura"] = "AGOTADO"
        
    # Search Accident Date
    date_match = re.search(rf"INFORMACIÓN DEL ACCIDENTADO.*?(?:Fecha\s*accidente\s*.*?|(?:{tipos_id})\s+\d+.*?)(\d{{2}}[-/]\d{{2}}[-/]\d{{4}})", text, re.IGNORECASE | re.DOTALL)
    data["Fecha Siniestro"] = date_match.group(1) if date_match else "No encontrado"
    
    return data

def hdi(text):
    data = {}
    
    # Search Names and Lastnames
    match_names = re.search(r"Nombre de la víctima:\s*([A-ZÁÉÍÓÚÑ ]+)", text, re.IGNORECASE)
    data["Nombres y Apellidos"] = match_names.group(1) if match_names else "No encontrado"
    
    # Search number ID
    match_id = re.search(r"Número Id víctima:\s*(\d+)", text, re.IGNORECASE)
    data["Identificacion"] = match_id.group(1).replace(".", "") if match_id else "No encontrado"
    
    # Search Policy Number
    policy_match = re.search(r"Póliza:\s*(\d+)", text, re.IGNORECASE)
    data["Numero Poliza"] = policy_match.group(1) if policy_match else "No encontrado"
    
    # Search Total Value
    total_paid_match = re.search(r"Valor\s*total\s*pagado\s*:\s*\$\s*([\d.,]+)", text, re.IGNORECASE)
    data["Valor Total Pagado"] = total_paid_match.group(1) if total_paid_match else "No encontrado"
    
    # Search Accident Date
    date_match = re.search("(?i)Fecha\s*(?:de\s*)?accidente\s*:?\s*(\d{2}[-/]\d{2}[-/]\d{4})", text)
    data["Fecha Siniestro"] = date_match.group(1) if date_match else "No encontrado"
    
    return data

def indemnizaciones(text):
    data = {}
    
    # Search Names and Last Names
    name_match = re.search(r"(?:La señora|El señor)\s+([A-Za-zÁÉÍÓÚÑáéíóúñ ]+),\s*identificad[ao] con", text, re.IGNORECASE)
    data["Nombres y Apellidos"] = name_match.group(1).strip() if name_match else "No encontrado"
    
    # Search ID
    id_match= re.search(r"Cédula de\s+Ciudadanía[\s\n]*([\d\.,]+)", text, re.IGNORECASE)
    data["Identificacion"] = id_match.group(1).replace(".", "") if id_match else "No encontrado"
    
    # Search policy number
    policy_match = re.search(r"POLIZA SOAT No\.\s*(\d+)", text,re.IGNORECASE)
    data["Numero Poliza"] = policy_match.group(1) if policy_match else "No encontrado"
    
    # Search Medical expenses
    no_present_match = re.search(r"NO HA PRESENTADO PAGOS POR CONCEPTOS DE GASTOS MEDICOS", text, re.IGNORECASE)
    data["Concepto Gastos"] = "NO HA PRESENTADO GASTOS MÉDICOS" if no_present_match else "No encontrado"

    return data

def bolivar(text):
    data = {}
    
    #Search names, last names and type of ID
    name_match = re.search(r"([A-Z]{2,})\s+(\d+)\s+([A-ZÁÉÍÓÚÑ\s]+?)\s+\d{2}-\d{2}-\d{4}", text, re.IGNORECASE | re.DOTALL)
    if name_match:
        data["Nombres y Apellidos"] = name_match.group(3).strip()
        data["Identificación"] = name_match.group(2).strip()
        data["Tipo Identificación"] = name_match.group(1).strip()
    else:
        data.update({
            "Nombres y Apellidos": "No Encontrado",
            "identificacion":"No Encontrado",
            "Tipo Identificación": "No Encontrado"
        })
    
    # Search number policy
    policy_match = re.search(r"(?:Póliza\s+Número.*?(\d{13,})|(?:No\.|numero)\s*(\d+))", text, re.IGNORECASE | re.DOTALL)
    data["Numero Poliza"] = policy_match.group(1) if policy_match else "No encontrado"
    
    # Search coverage and total payable
    total_line_match = re.search(r"(\d+\.\d+)\s+\$\s+([\d.]+)\s+\$\s+([\d.]+)", text)
    if total_line_match:
        data["Cobertura"] = total_line_match.group(2)
        data["Valor Pagado"] = total_line_match.group(3)
    else:
        data["Cobertura"] = "No encontrado"
        data["Valor Pagado"] = "No encontrado"
    
    valor_pagado = int(data["Valor Pagado"].replace(".", ""))
    cobertura = int(data["Cobertura"].replace(".", ""))
    if valor_pagado >= cobertura:
        data["Estado Cobertura"] = "AGOTADO"
    else:
        data["Estado Cobertura"] = "NO AGOTADO"
    
    # Search accident Date
    match_date = re.search(r"Fecha Accidente.*?(\d{2}-\d{2}-\d{4})", text, re.DOTALL)
    data["Fecha Siniestro"] = match_date.group(1) if match_date else "No encontrado"
    
    return data

def seg_mundial(text):
    data = {}
    
    #Search Names and Lastnames
    name_last_match = re.compile(
        r"(?:^|\n)(?!AGOTADA\b)([A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+)*)(?:\s+GASTOS (?:DE|MEDICOS))(?:(?!GASTOS)[^\n]*)\n?([A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+)*)?",
        re.MULTILINE | re.DOTALL)
    name_match = name_last_match.search(text)
    if name_match:
        name_complete = " ".join(filter(None, [name_match.group(1), name_match.group(2)])).strip()
        name_complete = re.sub(r"\b(TRANSPORTE|GERENTE|DE|1)\b", "", name_complete).strip()
        data={"Nombre Completo": name_complete}
    else:
        data = {"Nombre Completo": "No Encontrado"}
        
    #Search a Coverage Status
    status_match = re.search(r"(?i)GASTOS MEDICOS.*?\n.*?(NO AGOTADA|AGOTADA)", text, re.MULTILINE)
    data["Estado Cobertura"] = status_match.group(1) if status_match else "No encontrado"
    
    #Search a policy Number
    policy_match = re.search(r"""
                        .*GASTOS\s+MEDICOS\s+               # Busca "GASTOS MEDICOS" en la línea (puede haber texto antes)
    \d{1,2}\/\d{1,2}\/\d{2,4}\s+         # Fecha (formato flexible)
    (?P<parte1>[0-9\-]+)                # Captura la primera parte del número de póliza
    [^\n]*\n                          # Resto de la línea hasta el salto de línea
    (?:[A-ZÁÉÍÓÚÑ\s]+)\s+              # Coincide con el nombre (en mayúsculas, ajusta si es necesario)
    (?P<parte2>\d+) 
                            """, 
                            text,
                            re.VERBOSE | re.MULTILINE)
    if policy_match:
        policy_number_one = policy_match.group("parte1")
        policy_number_two = policy_match.group("parte2")
        policy_number_complete = f"{policy_number_one} {policy_number_two}"
        data["Numero de Poliza"] = policy_number_complete
    else:
        policy_number = "No encontrado"
        data["Numero de Poliza"] = policy_number
        
    #Search a Accident Date
    date_match = re.search("GASTOS MEDICOS\s+(\d{2}/\d{2}/\d{4})", text)
    data["Fecha Siniestro"] = date_match.group(1).strip() if date_match else "No encontrado"
    
    return data

def colpatria_axa(text):
    data = {}
    
    name_match = re.search(r"Lesionado \(a\) : (.*)", text, re.IGNORECASE)
    data["Nombres y Apellidos"] = name_match.group(1).strip() if name_match else None
    
    type_id = re.search(r"Tipo ID Lesionado : (.*)", text, re.IGNORECASE)
    data["Tipo de identificación"] = type_id.group(1).strip() if type_id else None
    
    number_id = re.search(r"Numero de ID Lesionado : (.*)", text, re.IGNORECASE)
    data["Numero de identificación"] = number_id.group(1).strip() if number_id else None
    
    accident_date = re.search(r"Fecha Ocurrencia : (.*)", text, re.IGNORECASE)
    data["Fecha de incidente"] = accident_date.group(1).strip() if accident_date else None
    
    number_policy = re.search(r"No\. Póliza : (.*)", text, re.IGNORECASE)
    data["Numero de Poliza"] = number_policy.group(1).strip() if number_policy else None
    
    status = re.search(r"(AGOTADO|NO AGOTADO)", text, re.IGNORECASE)
    data["Estado de Cobertura"] = status.group(1).strip() if status else None
    
    return data

def seg_estados(text):
    data={}

    afectado_match= re.search(r"AFECTADO\s+(\d+)-([^\n]+)", text, re.IGNORECASE)
    if afectado_match:
        data["Numero ID"] = afectado_match.group(1)
        data["Nombre y Apellido"] = afectado_match.group(2)
    else:
        data["Nombre y Apellido"] = None
        data["Numero ID"] = None

    number_policy = re.search(r"No\.\s*(\d+)", text, re.IGNORECASE)
    data["Numero de Poliza"] = number_policy.group(1) if number_policy else None

    date = re.search(r"FECHA DE SINIESTRO\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    data["Fecha Siniestro"] = date.group(1) if date else None

    coverage = re.search(r"ESTADO Cobertura\s+(.*?)(?=\n|$)", text, re.IGNORECASE)
    data["Estado de Cobertura"] = coverage.group(1) if coverage else None

    return data

def solidaria(text):
    data ={}

    id_name_match = re.search(r"(CC|TI|CE|PE|NIT|AS|DE|MS|CN)\s+(\d+)\s+([A-ZÁÉÍÓÚÑ\s]+?)\s+(\d{2}-\d{2}-\d{4})", 
                            text, re.IGNORECASE)
    if id_name_match:
        data["Nombre y Apellido"] = id_name_match.group(3).strip().title()
        data["Tipo ID"] = id_name_match.group(1).strip().upper()
        data["Numero ID"] = id_name_match.group(2).strip()
        data["Fecha de Siniestro"] = id_name_match.group(4).strip()
    else:
        data["Nombre y Apellido"] = None
        data["Tipo ID"] = None
        data["Numero ID"] = None
        data["Fecha de Siniestro"] = None
    
    coverage_match = re.search(r"Valor Disponible.*?(\bAGOTADO\b|\bNO AGOTADO\b)", text, re.DOTALL|re.IGNORECASE)
    data["Estado de Cobertura"] = coverage_match.group(1).strip() if coverage_match else None

    policy_match = re.search(r"Póliza Número\D+(\d+)", text)
    data["Numero de Poliza"] = policy_match.group(1).strip() if policy_match else None

    return data

# Extraction process 
def extract_data(text, pdf_file):
    if re.search(r"MAPFRE SEGUROS GENERALES DE COLOMBIA", text, re.IGNORECASE):
        data = Mapfre(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"PREVISORA S.A.", text, re.IGNORECASE):
        data = previsora(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"SURAMERICANA S.A", text, re.IGNORECASE):
        data = sura(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"HDI SEGUROS COLOMBIA", text, re.IGNORECASE):
        data = hdi(text)
        return {**data, "Nombre archivo": pdf_file}
    elif re.search(r"LLAC", text, re.IGNORECASE):
        data= indemnizaciones(text)
        return {**data, "Nombre archivo":pdf_file}
    elif re.search(r"SEGUROS\s+BOLIVAR\b.*?S\.A\.", text, re.IGNORECASE|re.DOTALL):
        data = bolivar(text)
        return {**data, "Nombre archivo":pdf_file}
    elif re.search(r"SEGUROS MUNDIAL", text, re.IGNORECASE):
        data = seg_mundial(text)
        return {**data, "Nombre archivo":pdf_file}
    elif re.search(r"AXA COLPATRIA SEGUROS", text, re.IGNORECASE):
        data = colpatria_axa(text)
        return {**data, "Nombre archivo":pdf_file}
    elif re.search(r"(?i)SEGUROS DEL ESTADO S\.A\.", text):
        data = seg_estados(text)
        return {**data, 'Nombre archivo':pdf_file}
    elif re.search(r"ASEGURADORA SOLIDARIA DE COLOMBIA", text):
        data = solidaria(text)
        return {**data, 'Nombre archivo':pdf_file}
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
