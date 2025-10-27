def ionic_extraction():

    data = request.json
    print(f"Data recieved: {data}")
    try:
        tenant_id = data['tenant_id']
        case_id = data.get('case_id', None)
        process = data.get('tenant_id', None)
    except Exception as e:
        print(f'## TE Received unknown data. [{data}] [{e}]')
        return {'flag': False, 'message': 'Incorrect Data in request'}

    db_config['tenant_id'] = tenant_id
    extraction_db = DB('extraction', **db_config)
    queue_db = DB('queues', **db_config)    

    container_name = data.get('container', None)

    try:

        query = f"SELECT `document_id`  from  `process_queue` where `case_id` = '{case_id}';"
        document_ids=queue_db.execute_(query)["document_id"].to_list()
        # print(f"The result is {document_ids}")
        
        for document_id in document_ids:

            query = f"SELECT format_type,template_name,format_pages from  `ocr` where `case_id` = '{case_id}' and document_id ='{document_id}'"
            ocr_data=extraction_db.execute_(query)
            # print(f"The result is {ocr_data}")
            
            queue_db = DB('queues', **db_config)
            template_db = DB('template_db', **db_config)

            query = f"SELECT `ocr_word`,ocr_data from  `ocr_info` where `case_id` = '{case_id}'and document_id ='{document_id}'"
            ocr_data_all = queue_db.execute_(query)['ocr_word'].to_list()[0]
            ocr_data_all=json.loads(ocr_data_all)
            ocr_all = queue_db.execute_(query)['ocr_data'].to_list()[0]
            ocr_all=json.loads(ocr_all)

            format_types=ocr_data.to_dict(orient='records')

            for format_data in format_types:

                act_format_data=format_data['format_type']
                # print(f"format extarction is going start for {act_format_data}")

                format_page=format_data['format_type']
                identifier=format_data['template_name']

                extracted_table={}
                extracted_fields={}
                fields_highlights={}

                if not format_page or not identifier:
                    continue

                # print(F"foramt got is {format_page.rsplit('_', 1)}")
                format= format_page.rsplit('_', 1)[0]
                pages=format_page.rsplit('_', 1)[1]
                start=int(pages.split('@')[0])
                end=int(pages.split('@')[1])
                # print(f'start is {start} and end is {end}')
                ocr_pages=[]
                for pag in ocr_data_all:
                    if not pag:
                        continue
                    page_no=int(pag[0]['pg_no'])-1
                    if start<=page_no<=end:
                        print(start,page_no,end)
                        ocr_pages.append(pag)
                
                ocr_data_pages=[]
                for pag in ocr_all:
                    if not pag:
                        continue
                    page_no=int(pag[0]['pg_no'])-1
                    if start<=page_no<=end:
                        ocr_data_pages.append(pag)

                query = f"SELECT * from  `trained_info` where format='{format}' and identifier='{identifier}'"
                process_trained_fields = template_db.execute_(query).to_dict(orient='records')

                if process_trained_fields:
                    process_trained_fields=process_trained_fields[0]
                    # print(f"ocr_pages sending are {ocr_pages}")
                    start_pages=predict_mutli_checks(ocr_pages,ocr_data_pages,process_trained_fields,end)

                    if len(start_pages)>1:

                        del_rec=f'delete from ocr where case_id ="{case_id}" and format_type ="{format_page}"'
                        extraction_db.execute_(del_rec)

                        for pair in start_pages:
                            if len(pair)==1:
                                end_page=end
                            else:
                                end_page=pair[1]
                            start_page=pair[0]

                            formated=format+'_'+str(start_page)+'@'+str(end_page)
                            ne_pages=extract_page_list(formated)
                            query = "insert into `ocr` (template_name,case_id,format_type,document_id,format_pages) values (%s,%s,%s,%s,%s)"
                            params = [identifier,case_id, formated,case_id,json.dumps(ne_pages)]
                            extraction_db.execute_(query,params=params)

            query = f"SELECT format_type,template_name,format_pages from  `ocr` where `case_id` = '{case_id}' and document_id ='{document_id}'"
            case_data=extraction_db.execute_(query)

            format_types=case_data.to_dict(orient='records')
            
            for format_data in format_types:

                act_format_data=format_data['format_type']
                # print(f"format extarction is going start for {act_format_data}")

                format_page=format_data['format_type']
                identifier=format_data['template_name']

                extracted_table={}
                extracted_fields={}
                fields_highlights={}

                if not format_page:
                    continue

                # print(F"foramt got is {format_page.rsplit('_', 1)}")
                format= format_page.rsplit('_', 1)[0]
                pages=format_page.rsplit('_', 1)[1]
                start=int(pages.split('@')[0])
                end=int(pages.split('@')[1])
                # print(f'start is {start} and end is {end}')
                ocr_pages=[]
                for pag in ocr_data_all:
                    if not pag:
                        continue
                    page_no=int(pag[0]['pg_no'])-1
                    if start<=page_no<=end:
                        print(start,page_no,end)
                        ocr_pages.append(pag)
                
                ocr_data_pages=[]
                for pag in ocr_all:
                    if not pag:
                        continue
                    page_no=int(pag[0]['pg_no'])-1
                    if start<=page_no<=end:
                        ocr_data_pages.append(pag)

                if not ocr_pages or not ocr_data_pages:
                    continue

                print(f'len of ocr pages {len(ocr_pages)}')
                print(f'len of ocr pages {len(ocr_data_pages)}')

                # print(F" ########## exarction starting for foramt {format} and start and end pages got are {start} {end}")

                query = f"SELECT * from  `process_training_data` where format='{format}' and model_usage = 'yes'"
                master_process_trained_fields = template_db.execute_(query)

                if not master_process_trained_fields.empty:
                    master_process_trained_fields=master_process_trained_fields.to_dict(orient='records')[0]
                else:
                    master_process_trained_fields={}
                
                query = f"SELECT * from  `trained_info` where format='{format}' and identifier='{identifier}'"
                process_trained_fields = template_db.execute_(query)
                
                used_version=''
                if process_trained_fields.empty:
                    extarction_from={}

                    print(f'skkiping the eod {format_page}')
                    if start==end and format == 'eob':
                        print(f'skkiping the eod {format_page}')
                        continue

                    if not master_process_trained_fields:
                        continue

                    process_trained_fields=master_process_trained_fields
                    trained=process_trained_fields['trained']
                    process_trained_fields['values']=process_trained_fields['values_trained']
                    common_fields=process_trained_fields['fields_common']
                    
                    if trained:
                        print(F" ################# creating models real_time")
                        create_models_real_time(process,format,process_trained_fields,case_id)

                        extracted_fields,fields_highlights,extracted_headers=get_master_extraction_values(process,format,case_id,ocr_pages,json.loads(master_process_trained_fields['fields']),common_fields)
                        used_version='1'

                        query=f'update ocr set extracted_headers = %s where case_id = %s and format_type = %s'
                        extraction_db.execute_(query,params=[json.dumps(extracted_headers),case_id,format_page])

                    else:
                        if process_trained_fields['fields']:
                            fields=json.loads(process_trained_fields['fields'])
                            print(F" we dont ave any master template so fields are not extarcted so {fields}")
                            for field in fields:
                                extracted_fields[field]=''
                                
                else:
                    process_trained_fields=process_trained_fields.to_dict(orient='records')
                    extracted_table={}
                    extracted_fields={}
                    extarction_from={}
                    extracted_remarks={}
                    remarks_high={}

                    if process_trained_fields:
                        process_trained_fields= process_trained_fields[0]
                        #here we will extract any over all thing
                        fields_data = process_trained_fields['fields'] if process_trained_fields['fields'] else ''
                        if fields_data:
                            print(f'fields_data is {fields_data}')
                            extracted_fields['main_fields'], fields_highlights['main_fields'] = get_template_extraction_values(ocr_pages, ocr_data_pages, process_trained_fields, json.loads(fields_data))
                            # extracted_fields['main_fields'],fields_highlights['main_fields']=get_template_extraction_values(ocr_pages,ocr_data_pages,process_trained_fields,json.loads(process_trained_fields['fields']))
                            extarction_from['main_fields']=list(extracted_fields['main_fields'].keys())
                            print(F" #################### here table to extract is {fields_highlights['main_fields']}")
                        
                        if process_trained_fields['trained_table']:
                            process_trained_fields['trained_table']=json.loads(process_trained_fields['trained_table'])
                            for table_name,tables in process_trained_fields['trained_table'].items():
                                if len(tables)>2:
                                    table_header=tables[0]
                                    table_header_text=[]
                                    if 'table' in tables:
                                        table_header_text=tables[2]['table']['headers']
                                    elif 'headers' in tables[2]:
                                        table_header_text=tables[2]['headers']

                                    if table_header:
                                        found_header,table_headers_line=extract_table_header(ocr_data_pages,0,table_header,table_header_text=table_header_text)

                                    table_footer=tables[1]
                                    if table_footer:
                                        found_footer,table_foot_line=extract_table_header(ocr_data_pages,0,table_footer,True)

                                    if found_header:
                                        if found_footer:
                                            bottom=found_footer[0]['top']
                                        else:
                                            bottom=1000
                                        extracted_table,table_high=extract_table_from_header(extraction_db,template_db,case_id,ocr_data_pages,found_header,table_headers_line,0,bottom)
                                        # print(F" extracted_table #################### {extracted_table}")

                                        # if 'table' in table_high:
                                        #     fields_highlights['main_fields']['table']=table_high['table']
                                        #     extracted_fields['main_fields']['table']=extracted_table

                        remarks=process_trained_fields.get('remarks',{})
                        print(f' remarks need to be extracted are {remarks}')
                        if remarks:
                            print(f'remarks here are {remarks}')
                            remarks=json.loads(remarks)
                            if remarks and remarks.get('type','None') == 'check level':
                                extracted_remarks,remarks_high=extract_remarks(remarks.get('start',[]),remarks.get('end',[]),ocr_pages)

                        #here we will extract any sessions things
                        # print(F" here extract for section {process_trained_fields['sub_template_identifiers']}")
                        if process_trained_fields['sub_template_identifiers']:

                            sub_template_identifiers=json.loads(process_trained_fields['sub_template_identifiers'])
                            all_section_fields=json.loads(process_trained_fields['section_fields'])
                            table=json.loads(process_trained_fields['section_table'])

                            try:
                                table_t2=json.loads(process_trained_fields['section_table_t2'])
                            except:
                                table_t2={}

                            if table_t2:
                                print(f'this table has a t2 trained table')
                                table=table_t2

                            print(F" all_section_fields {all_section_fields}")

                            for section,identifiers in sub_template_identifiers.items():

                                if not all_section_fields:
                                    continue

                                section_fields=all_section_fields[section]

                                extarction_from[section]=[]
                                # print(F" section #################### {section}")
                                extracted_fields[section]=[]
                                fields_highlights[section]=[]
                                section_header=[]
                                if 'section_exceptions' in  identifiers:
                                    section_header=identifiers['section_exceptions']

                                if 'sub_section' in  identifiers and identifiers['sub_section']:
                                    sub_section=identifiers['sub_section']
                                    sub_section_identifiers=sub_section['identifiers']
                                    sub_section_fields=sub_section['selected_fields']

                                paraFieldsTraining={}
                                if 'paraFieldsTraining' in  identifiers and identifiers['paraFieldsTraining']:
                                    paraFieldsTraining=identifiers['paraFieldsTraining']

                                # print(F"################N section_header is {section_header}")
                                sub_templates,cordinates,all_ocr_sections,remarks_section_ocr=predict_sub_templates(identifiers['section_identifiers'],ocr_pages,ocr_data_pages,section_header,process_trained_fields)
                                print(F" main section cordinates {cordinates}")
                                if not sub_templates:
                                    continue

                                section_no=-1
                                # print(F" #################### sub_templates {len(sub_templates)}")
                                claim_ids=[]
                                for template_ocr in sub_templates:
                                    
                                    if 'sub_section' in  identifiers and identifiers['sub_section']:

                                        section_no=section_no+1

                                        sub_section=identifiers['sub_section']
                                        sub_section_identifiers=sub_section['identifiers']
                                        common_section_fields=sub_section['selected_fields']

                                        common_template_fields={}
                                        common_template_highlights={}
                                        if common_section_fields:
                                            common_template_fields['fields'],common_template_highlights['fields']=get_template_extraction_values(list(template_ocr.values()),list(all_ocr_sections[section_no].values()),process_trained_fields,section_fields,common_section=True,common_section_fields=common_section_fields)
                                        print(f'common_fields is {common_template_fields}')

                                        sub_sub_templates,sub_cordinates,sub_all_ocr_sections,sub_remarks_section_ocr=predict_sub_sub_templates(sub_section_identifiers,list(template_ocr.values()),list(all_ocr_sections[section_no].values()))
                                        print(F" sub section cordinates {sub_cordinates}")
                                        #loop for sub sub section starts here 

                                        sub_section_no=-1
                                        for sub_template_ocr in sub_sub_templates:

                                            sub_section_no=sub_section_no+1
                                            template_fields={}
                                            template_highlights={}
                                            if not sub_template_ocr:
                                                continue

                                            print(F" #################### sub_section_no is {sub_section_no}")
                                            print(F" #################### ocr_data is {list(sub_template_ocr.values())}")

                                            template_fields['fields'],template_highlights['fields']=get_template_extraction_values(list(sub_template_ocr.values()),list(sub_all_ocr_sections[sub_section_no].values()),process_trained_fields,section_fields,sub_section=True,common_section_fields=common_section_fields)

                                            if common_template_fields:
                                                template_fields['fields'].update(common_template_fields['fields'])
                                                template_highlights['fields'].update(common_template_highlights['fields'])

                                            print(f"template_fields is {template_fields['fields']}")

                                            extarction_from[section].append(list(template_fields['fields'].keys()))
                                            # print(F" #################### template_fields {template_fields}")
                                            # print(F" #################### cordinates {cordinates} and section_no {section_no}")

                                            if section in table and table[section]:
                                                print(F"section is {section}")
                                                # print(F" #################### cordinates {cordinates} and section_no {section_no}")
                                                page_no=sub_cordinates[sub_section_no][0]
                                                section_top=sub_cordinates[sub_section_no][1]
                                                trained_tables=table[section]
                                                print(F"trained_tables is {trained_tables}")
                                                template_fields['table']={}
                                                template_highlights['table']={}

                                                # print(" ################ all_ocr_sections start line is",all_ocr_sections[section_no])
                                                table_extract=False
                                                max_match=0
                                                needed_table=''
                                                for table_name,tables in trained_tables.items():

                                                    print(F"table_name is  here is to idnetify the table {table_name}")

                                                    if table_name == 'table':
                                                        continue
                                                    if tables and len(tables)>2:
                                                        print(F"tables is {tables[0]}")
                                                        table_header=tables[0]
                                                        table_header_text=tables[2]
                                                        if 'table' in table_header_text:
                                                            table_header_text=table_header_text['table'].get('headers',[])
                                                        else:
                                                            table_header_text=table_header_text.get('headers',[])
                                                        header_lines=[]
                                                        if table_header:
                                                            header_lines=extract_table_header(list(sub_all_ocr_sections[sub_section_no].values()),section_top,table_header,table_header_text=table_header_text,header_check=True)
                                                            print(F"found_header is {header_lines}")
                                                            if not header_lines:
                                                                for ocr in ocr_all:
                                                                    if not pag:
                                                                        continue
                                                                    header_lines=extract_table_header([ocr],0,table_header,table_header_text=table_header_text,header_check=True)
                                                                    print(F"found_header is {header_lines}")
                                                                    if header_lines:
                                                                        break
                                                        if header_lines:
                                                            table_headers_line=line_wise_ocr_data(table_header)
                                                            table_line_words=''
                                                            for table_head_line in table_headers_line:
                                                                for word in table_head_line:
                                                                    table_line_words=table_line_words+" "+word['word']
                                                            print(F"table_line_words is {table_line_words}")

                                                            header_lines_found=line_wise_ocr_data(header_lines)
                                                            headee_line_words=''
                                                            for header_line_found in header_lines_found:
                                                                for word in header_line_found:
                                                                    headee_line_words=headee_line_words+" "+word['word']
                                                            print(F"headee_line_words is {headee_line_words}")
                                                        
                                                            matcher = SequenceMatcher(None, table_line_words, headee_line_words)
                                                            similarity_ratio_col = matcher.ratio()
                                                            print(F"similarity_ratio_col is {similarity_ratio_col} for the tabke is {table_name}")

                                                            if similarity_ratio_col>max_match:
                                                                max_match=similarity_ratio_col
                                                                needed_table=table_name

                                                for table_name,tables in trained_tables.items():

                                                    if table_name == 'table':
                                                        continue

                                                    if needed_table and needed_table !=table_name:
                                                        continue


                                                    trained_map={}
                                                    needed_headers=[]
                                                    if tables and len(tables)>3:
                                                        trained_map_got=tables[3]
                                                        # print(F"trained_map is {trained_map_got}")
                                                        trained_map={}
                                                        for key,value in trained_map_got.items():
                                                            if key.startswith("New Column") and value.startswith("New Column"):
                                                                continue
                                                            if key.startswith("New Column"):
                                                                trained_map[value] = value
                                                            else:
                                                                trained_map[key] = value
                                                        # print(F"trained_map is {trained_map}")

                                                    extra_variables=[]
                                                    if tables and len(tables)>4:
                                                        extra_variables=tables[4]
                                                    print(F"extra_variables is {extra_variables}")

                                                    no_header_columns=[]
                                                    if tables and len(tables)>5:
                                                        no_header_columns=tables[5]
                                                    print(F"no_header_columns is {no_header_columns}")
                                                        
                                                    if tables and len(tables)>2:
                                                        print(F"tables is {tables[0]}")
                                                        table_header=tables[0]
                                                        table_header_text=tables[2]
                                                        if 'table' in table_header_text:
                                                            table_header_text=table_header_text['table'].get('headers',[])
                                                        else:
                                                            table_header_text=table_header_text.get('headers',[])

                                                        if trained_map:
                                                            trained_map = dict(
                                                                sorted(
                                                                    trained_map.items(),
                                                                    key=lambda x: (table_header_text.index(x[0]) if x[0] in table_header_text else
                                                                                table_header_text.index(x[1]) if x[1] in table_header_text else float('inf'))
                                                                )
                                                            )
                                                            table_header_text=trained_map.values()
                                                            needed_headers=trained_map.keys()

                                                        if table_header:
                                                            head_page=[]
                                                            found_header,table_headers_line=extract_table_header(list(sub_all_ocr_sections[sub_section_no].values()),section_top,table_header,table_header_text=table_header_text)
                                                            print(F"found_header is {found_header}")
                                                            if not found_header:
                                                                for ocr in ocr_all:
                                                                    if not pag:
                                                                        continue
                                                                    found_header,table_headers_line=extract_table_header([ocr],0,table_header,table_header_text=table_header_text)
                                                                    print(F"found_header is {found_header}")
                                                                    if found_header:
                                                                        break
                                                        

                                                        table_footer=tables[1]
                                                        found_footer=None
                                                        if table_footer:
                                                            found_footer,table_foot_line=extract_table_header(list(sub_all_ocr_sections[sub_section_no].values()),section_top,table_footer,True)
                                                        
                                                        if found_header:
                                                            if found_footer:
                                                                bottom=found_footer[0]['top']
                                                                bottom_page=found_footer[0]['pg_no']
                                                            else:
                                                                bottom=1000
                                                                bottom_page=False
                                                            print(F"found_header is {found_header}")
                                                            print(F"found_footer is {found_footer}")

                                                            template_extracted_table,table_high=extract_table_from_header(extraction_db,template_db,case_id,list(sub_all_ocr_sections[sub_section_no].values()),found_header,table_headers_line,section_top,bottom=bottom,cord=sub_cordinates[sub_section_no],trained_map=trained_map,bottom_page=bottom_page,extra_variables=extra_variables,no_header_columns=no_header_columns)
                                                            print(F" template_extracted_table #################### {template_extracted_table}")

                                                            # if needed_headers:
                                                            #     template_extracted_table=filter_columns(template_extracted_table, needed_headers)

                                                            if 'table' in table_high:
                                                                template_highlights['table'][table_name]=table_high['table']

                                                            template_fields['table'][table_name]=template_extracted_table
                                                        else:
                                                            template_fields['table'][table_name]={}

                                                        if template_fields['table'][table_name]:
                                                            table_extract=True
                                                            break

                                                if not table_extract:
                                                    template_fields['table']={}
                                                    template_fields['table']['table_1']={}

                                                print(f' remarks need to be extracted are {remarks}')
                                                if remarks and remarks.get('type','None') == 'claim level':
                                                    extracted_remarks,remarks_high=extract_remarks(remarks.get('start',[]),remarks.get('end',[]),list(remarks_section_ocr[section_no].values()))

                                                if extracted_remarks:
                                                    template_fields['remarks']=extracted_remarks
                                                    template_highlights['remarks']=remarks_high

                                            fields_highlights[section].append(template_highlights)
                                            extracted_fields[section].append(template_fields)

                                    else:
                                        template_fields={}
                                        template_highlights={}

                                        if not template_ocr:
                                            continue

                                        section_no=section_no+1
                                        print(F" #################### section_no is {section_no}")
                                        print(F" #################### ocr_data is {list(template_ocr.values())}")

                                        section_fields=all_section_fields[section]
                                        template_fields['fields'],template_highlights['fields']=get_template_extraction_values(list(template_ocr.values()),list(all_ocr_sections[section_no].values()),process_trained_fields,section_fields,section_fields=True)
                                        extarction_from[section].append(list(template_fields['fields'].keys()))
                                        # print(F" #################### template_fields {template_fields}")
                                        # print(F" #################### cordinates {cordinates} and section_no {section_no}")

                                        if section in table and table[section]:

                                            # print(F" #################### cordinates {cordinates} and section_no {section_no}")
                                            page_no=cordinates[section_no][0]
                                            section_top=cordinates[section_no][1]
                                            trained_tables=table[section]
                                            template_fields['table']={}
                                            template_highlights['table']={}

                                            # print(" ################ all_ocr_sections start line is",all_ocr_sections[section_no])
                                            table_extract=False
                                            max_match=0
                                            needed_table=''
                                            print(F"trained_tables is {trained_tables}")
                                            for table_name,tables in trained_tables.items():
                                                if table_name == 'table':
                                                    continue
                                                if tables and len(tables)>2:
                                                    print(F"tables is {tables[0]}")
                                                    table_header=tables[0]
                                                    table_header_text=tables[2]
                                                    if 'table' in table_header_text:
                                                        table_header_text=table_header_text['table'].get('headers',[])
                                                    else:
                                                        table_header_text=table_header_text.get('headers',[])
                                                    header_lines=[]
                                                    if table_header:
                                                        header_lines=extract_table_header(list(all_ocr_sections[section_no].values()),section_top,table_header,table_header_text=table_header_text,header_check=True)
                                                        print(F"found_header is {header_lines}")
                                                        if not header_lines:
                                                            for ocr in ocr_all:
                                                                if not pag:
                                                                    continue
                                                                header_lines=extract_table_header([ocr],0,table_header,table_header_text=table_header_text,header_check=True)
                                                                print(F"found_header is {header_lines}")
                                                                if header_lines:
                                                                    break
                                                    if header_lines:
                                                        table_headers_line=line_wise_ocr_data(table_header)
                                                        table_line_words=''
                                                        for table_head_line in table_headers_line:
                                                            for word in table_head_line:
                                                                table_line_words=table_line_words+" "+word['word']
                                                        print(F"table_line_words is {table_line_words}")

                                                        header_lines_found=line_wise_ocr_data(header_lines)
                                                        headee_line_words=''
                                                        for header_line_found in header_lines_found:
                                                            for word in header_line_found:
                                                                headee_line_words=headee_line_words+" "+word['word']
                                                        print(F"headee_line_words is {headee_line_words}")
                                                    
                                                        matcher = SequenceMatcher(None, table_line_words, headee_line_words)
                                                        similarity_ratio_col = matcher.ratio()
                                                        print(F"similarity_ratio_col is {similarity_ratio_col}")
                                                        if similarity_ratio_col>max_match:
                                                            needed_table=table_name


                                            for table_name,tables in trained_tables.items():

                                                if table_name == 'table':
                                                    continue

                                                print(f'needed table is {needed_table}')
                                                if needed_table and needed_table !=table_name:
                                                    continue


                                                trained_map={}
                                                needed_headers=[]
                                                if tables and len(tables)>3:
                                                    trained_map_got=tables[3]
                                                    # print(F"trained_map is {trained_map_got}")
                                                    trained_map={}
                                                    for key,value in trained_map_got.items():
                                                        if key.startswith("New Column"):
                                                            trained_map[value] = value
                                                        elif value.startswith("New Column"):
                                                            trained_map[key] = key
                                                        else:
                                                            trained_map[key] = value
                                                    # print(F"trained_map is {trained_map}")

                                                extra_variables=[]
                                                if tables and len(tables)>4:
                                                    extra_variables=tables[4]
                                                print(F"extra_variables is {extra_variables}")

                                                no_header_columns=[]
                                                if tables and len(tables)>5:
                                                    no_header_columns=tables[5]
                                                print(F"no_header_columns is {no_header_columns}")
                                                    
                                                if tables and len(tables)>2:
                                                    table_header=tables[0]
                                                    table_header_text=tables[2]
                                                    if 'table' in table_header_text:
                                                        table_header_text=table_header_text['table'].get('headers',[])
                                                    else:
                                                        table_header_text=table_header_text.get('headers',[])

                                                    if trained_map:
                                                        trained_map = dict(
                                                            sorted(
                                                                trained_map.items(),
                                                                key=lambda x: (table_header_text.index(x[0]) if x[0] in table_header_text else
                                                                            table_header_text.index(x[1]) if x[1] in table_header_text else float('inf'))
                                                            )
                                                        )
                                                        table_header_text=trained_map.values()
                                                        needed_headers=trained_map.keys()

                                                    found_header=[]
                                                    print(F"table_header is {table_header}")
                                                    if table_header:
                                                        head_page=[]
                                                        found_header,table_headers_line=extract_table_header(list(all_ocr_sections[section_no].values()),section_top,table_header,table_header_text=table_header_text)
                                                        print(F"found_header is here is{found_header}")

                                                        if found_header:
                                                            extra_headers=[]
                                                            found_extra_headers=[]
                                                            second_header_box=[]
                                                            if tables and len(tables)>6:
                                                                extra_headers=tables[6]
                                                            print(F"extra_headers is {extra_headers}")

                                                            header_page=found_header[0]['pg_no']
                                                            needed_ocr=[]
                                                            for page in list(all_ocr_sections[section_no].values()):
                                                                if page and page[0]['pg_no']==header_page:
                                                                    needed_ocr.append(page)

                                                            if extra_headers:
                                                                found_extra_headers,second_header_box=find_extra_headers(extra_headers,needed_ocr)

                                                        if not found_header:
                                                            for ocr in ocr_all:
                                                                if not pag:
                                                                    continue
                                                                found_header,table_headers_line=extract_table_header([ocr],0,table_header,table_header_text=table_header_text)
                                                                print(F"found_header is here is {found_header}")
                                                                if found_header:
                                                                    extra_headers=[]
                                                                    found_extra_headers=[]
                                                                    second_header_box=[]
                                                                    if tables and len(tables)>6:
                                                                        extra_headers=tables[6]
                                                                    print(F"extra_headers is here is {extra_headers}")

                                                                    found_extra_headers,second_header_box=find_extra_headers(extra_headers,[ocr])
                                                                    break
                                                    

                                                    table_footer=tables[1]
                                                    found_footer=None
                                                    print(F"table_footer is {table_footer}")
                                                    if table_footer:
                                                        found_footer,table_foot_line=extract_table_header(list(all_ocr_sections[section_no].values()),section_top,table_footer,True)
                                                    
                                                    if found_header:

                                                        if found_footer:
                                                            bottom=found_footer[0]['top']
                                                            bottom_page=found_footer[0]['pg_no']
                                                        else:
                                                            bottom=1000
                                                            bottom_page=False
                                                        print(F"found_header is {found_header}")
                                                        print(F"found_footer is {found_footer}")

                                                        template_extracted_table,table_high=extract_table_from_header(extraction_db,template_db,case_id,list(all_ocr_sections[section_no].values()),found_header,table_headers_line,section_top,bottom=bottom,cord=cordinates[section_no],trained_map=trained_map,bottom_page=bottom_page,extra_variables=extra_variables,no_header_columns=no_header_columns,found_extra_headers=found_extra_headers,second_header_box=second_header_box)
                                                        print(F" template_extracted_table #################### {template_extracted_table}")

                                                        # if needed_headers:
                                                        #     template_extracted_table=filter_columns(template_extracted_table, needed_headers)

                                                        if 'table' in table_high:
                                                            template_highlights['table'][table_name]=table_high['table']

                                                        template_fields['table'][table_name]=template_extracted_table
                                                    else:
                                                        template_fields['table'][table_name]={}

                                                    if template_fields['table'][table_name]:
                                                        table_extract=True
                                                        break


                                            if not table_extract:
                                                template_fields['table']={}
                                                template_fields['table']['table_1']={}


                                            print(f' remarks need to be extracted are {remarks}')
                                            if remarks and remarks.get('type','None') == 'claim level':
                                                extracted_remarks,remarks_high=extract_remarks(remarks.get('start',[]),remarks.get('end',[]),list(remarks_section_ocr[section_no].values()))

                                            if extracted_remarks:
                                                template_fields['remarks']=extracted_remarks
                                                template_highlights['remarks']=remarks_high


                                        if paraFieldsTraining:
                                            para_field,para_high=predict_paragraph(paraFieldsTraining,list(template_ocr.values()))
                                            print(para_field,'para_field')
                                            print(para_high,'para_high')
                                            for field,value in para_field.items():
                                                if field in template_fields['fields'] and value:
                                                    template_fields['fields'][field]=value
                                                    for field_high in template_highlights:
                                                        template_highlights['fields'][field_high]=para_high[field]

                                        fields_highlights[section].append(template_highlights)
                                        extracted_fields[section].append(template_fields)


                if extracted_fields:
                    update_into_db(tenant_id,extracted_fields,extracted_table,extraction_db,case_id,act_format_data,process,json.loads(master_process_trained_fields['fields']),used_version,document_id,extarction_from)
                    update_highlights(tenant_id,case_id,fields_highlights,act_format_data,document_id)
                
                # dir_path = os.path.join("/var/www/extraction_api/app/extraction_folder/", case_id)
                # try:
                #     # Delete the directory and its contents
                #     if os.path.exists(dir_path):
                #         shutil.rmtree(dir_path)
                #         print(f"Directory '{dir_path}' deleted successfully.")
                #     else:
                #         print(f"Directory '{dir_path}' does not exist.")
                        
                # except Exception as e:
                #     print(f"An error occurred while deleting the directory: {e}")

        #post Processing
        post_processing(extraction_db,queue_db,case_id)
    
        try:
            result_for_accuracy = checks_stored_field_acccuracy(tenant_id,case_id)
            print(f"#####result is {result_for_accuracy}")
        except Exception as e:
            print(f"##########Error is {e}")

        message="ionic_extraction api is sucessfull."

        container=load_controler(tenant_id,"business_rules")

        query = f"select no_of_process from load_balancer where container_name='{container}'"
        no_of_process = int(queue_db.execute_(query)['no_of_process'].to_list()[0])
        no_of_process=str(no_of_process+1)
        query=f"update load_balancer set no_of_process = '{no_of_process}' where container_name = '{container}'"
        queue_db.execute_(query)


        reponse = {"data":{"message":message,"container":container,'process_flag':'true'},"flag":True,"container":container,'process_flag':'true'}
    except Exception as e:
        queue_db.execute("update `process_queue` set  invalidfile_reason = %s where `case_id` = %s", params=[f"Error at Extraction Container",case_id])
    
        error_message = traceback.format_exc()
        print(f"########## Error is: {e}")
        print("########## Traceback details:")
        print(error_message)

        reponse = {"data":{"message":"Error at Extraction Container",'process_flag':'false'},"flag":True,'process_flag':'false'}

    query = f"select no_of_process from load_balancer where container_name='{container_name}'"
    no_of_process = int(queue_db.execute_(query)['no_of_process'].to_list()[0])
    no_of_process=str(no_of_process-1)
    query=f"update load_balancer set no_of_process = '{no_of_process}' where container_name = '{container_name}'"
    queue_db.execute_(query)

    return reponse
---------------------------------------------------------------------------------------------------------------------------------------------------------------------


def predict_mutli_checks(ocr_data_all_got,ocr_raw_pages,process_trained_fields,end):

    row_headers = process_trained_fields.get('row_headers', None)
    column_headers = process_trained_fields.get('column_headers', None)
    contexts = process_trained_fields.get('contexts', None)

    row_headers_t2 = process_trained_fields['row_headers_t2']
    column_headers_t2 = process_trained_fields['column_headers_t2']
    contexts_t2 = process_trained_fields['contexts_t2']

    # row_headers,column_headers,contexts=process_trained_fields['row_headers'],process_trained_fields['column_headers'],process_trained_fields['contexts']

    if column_headers:
        column_headers=json.loads(column_headers)
    else:
        column_headers={}
    if row_headers:
        row_headers=json.loads(row_headers)
    else:
        row_headers={}
    if contexts:
        contexts=json.loads(contexts)
    else:
        contexts={}

    if column_headers_t2:
        column_headers_t2=json.loads(column_headers_t2)
    else:
        column_headers={}
    if row_headers_t2:
        row_headers_t2=json.loads(row_headers_t2)
    else:
        row_headers_t2={}
    if contexts_t2:
        contexts_t2=json.loads(contexts_t2)
    else:
        contexts_t2={}
    
    
    extracted_fields={}

    fields=['Check Number','Check Amount']
    page_field_data={}

    for field in fields:

        print(F" #####################")
        print(F" #####################")
        print(F" #####################")
        print(F" ##################### fiels is {field}")
        print(F" #####################")
        print(F" #####################")
        print(F" #####################")

        extracted_fields[field]=''

        row_header_int=row_headers.get(field,[])
        context_int=contexts.get(field,[])

        row_header_int_t2=[]
        if row_headers_t2:
            row_header_int_t2=row_headers_t2.get(field,[])
        context_int_t2=[]
        if contexts_t2:
            context_int_t2=contexts_t2.get(field,[])

        print(f" ########### row_header_int_t2 got are  {row_header_int_t2}")
        print(f" ########### context_int_t2 got are  {context_int_t2}")


        if row_header_int_t2 and context_int_t2:
            row_header_int=row_header_int_t2
            context_int=context_int_t2

        print(f" ########### row_header_int got are  {row_header_int}")
        print(f" ########### context_int got are  {context_int}")

        context_box={}
        if 'context_box' in context_int:
            context_box=context_int['context_box']
        row_box={}
        if 'row_box' in row_header_int:
            row_box=row_header_int['row_box']
        value_box={}
        if 'value_box' in row_header_int:
            value_box=row_header_int['value_box']

        # print(F" ##################### len of ocr_data_all is {len(ocr_data_all)}")
        all_pairs_row_con=check_headers(row_header_int,context_int,copy.deepcopy(ocr_data_all_got),copy.deepcopy(ocr_raw_pages))

        for pair in all_pairs_row_con:

            row_header=pair[0]
            context=pair[2]

            print(f" ########### finalised_headers got are  {pair}")
            if not row_header:
                continue
        
            for ocr_word in ocr_data_all_got:
                if not ocr_word:
                    continue
                if ocr_word[0]['pg_no'] == row_header['pg_no']:
                    value_page_ocr_data=ocr_word
            
            if row_header:
                possible_values_row_got,multi_line=finding_possible_values(row_header,row_header_int,value_page_ocr_data)
                print(f" ################ possible_values_row got are {possible_values_row_got}")

            if value_box:
                possible_values_row=[]
                for value in possible_values_row_got:
                    if value_box['left']>=row_box['left'] and value['left']+10>=row_header['left']:
                        possible_values_row.append(value)
                    else:
                        possible_values_row.append(value)
            else:
                possible_values_row=possible_values_row_got
            print(f" ################ possible_values_row got are {possible_values_row}")

            max_calculated_diff=10000
        
            for value in possible_values_row:

                calculated_diff=0
                if row_header:
                    value_row_diff_cal=calculate_distance(row_header,value)
                    row_act_confidence=value_row_diff_cal
                    row_base_diff=row_header_int['value_thr']
                    row_conf=calculate_confidence(row_base_diff,row_act_confidence)
                
                    calculated_row_diff=abs(row_header_int['value_thr']-value_row_diff_cal)
                    calculated_diff=calculated_diff+calculated_row_diff

                if context:
                    
                    column_act_confidence=calculate_value_distance(context,value)
                    con_base_diff=context_int['value_thr']
                    con_conf=calculate_cont_confidence(con_base_diff,column_act_confidence)

                    value_con_diff_cal=calculate_value_distance(context,value)
                    calculated_con_diff=abs(context_int['value_thr']-value_con_diff_cal)
                    calculated_diff=calculated_diff+calculated_con_diff

            
                if max_calculated_diff>calculated_diff:
                    max_calculated_diff=calculated_diff
                    predicted=value

            print(f" ################ predicted value is {predicted['word']}")

            if predicted:
                pg = predicted['pg_no']
                page_field_data.setdefault(pg, {})[field] = predicted['word']

   # Now build ranges based on pages with required field count
    pages_with_checks = sorted([pg for pg, data in page_field_data.items()])
    print(f"pages_with_checks is {pages_with_checks}")
    print(f"page_field_data is {page_field_data}")

    ranges = []
    if pages_with_checks:
        # Filter out pages with no Check Number AND no Check Amount
        filtered_pages = []
        for pg in sorted(pages_with_checks):
            check_number = page_field_data.get(pg, {}).get("Check #", "")
            check_amount = page_field_data.get(pg, {}).get("Check Amount", "")
            if (check_number and re.sub(r'[^0-9]', '', check_number)) or (check_amount and re.sub(r'[^0-9]', '', check_amount)):
                filtered_pages.append(pg)

        if filtered_pages:
            # Decide whether to use Check Number or Check Amount
            use_check_number = any(
                page_field_data.get(pg, {}).get("Check #", "") and re.sub(r'[^0-9]', '', page_field_data.get(pg, {}).get("Check #", ""))
                for pg in filtered_pages
            )

            start_page = filtered_pages[0]
            prev_val = (
                re.sub(r'[^0-9]', '', page_field_data.get(start_page, {}).get("Check #", "")) 
                if use_check_number else 
                re.sub(r'[^0-9]', '', page_field_data.get(start_page, {}).get("Check Amount", ""))
            )

            for page in filtered_pages[1:]:
                curr_val = (
                    re.sub(r'[^0-9]', '', page_field_data.get(page, {}).get("Check #", "")) 
                    if use_check_number else 
                    re.sub(r'[^0-9]', '', page_field_data.get(page, {}).get("Check Amount", ""))
                )

                if curr_val != prev_val and curr_val:  # Change detected
                    ranges.append([start_page - 1, page - 2])
                    start_page = page
                    prev_val = curr_val

            # Add last range
            ranges.append([start_page - 1, end])

            print(f"Final ranges (filtered & based on {'Check #' if use_check_number else 'Check Amount'}): {ranges}")

    return ranges


-----------------------------------------------------------------------------------------------------------------------------------------------------------------



def create_models_real_time(process, format, process_trained_fields, case_id):
    column_header = json.loads(process_trained_fields['column_headers'])
    row_header = json.loads(process_trained_fields['row_headers'])
    context = json.loads(process_trained_fields['contexts'])
    values = json.loads(process_trained_fields['values'])
    others = json.loads(process_trained_fields['others'])

    dir_path = os.path.join("/var/www/extraction_api/app/extraction_folder/")
    os.makedirs(dir_path, exist_ok=True)
    print(f"Directory '{dir_path}' created successfully.")

    def process_part(part_data, others_input, file_prefix, is_value=False):
        try:
            json_file = f"{file_prefix}.json"
            model_file = f"{file_prefix}_logistic_regression_model.joblib"
            vectorizer_file = f"{file_prefix}_count_vectorizer.joblib"
            json_path = os.path.join(dir_path, json_file)
            model_path = os.path.join(dir_path, model_file)
            vectorizer_path = os.path.join(dir_path, vectorizer_file)

            if os.path.exists(json_path) and os.path.exists(model_path) and os.path.exists(vectorizer_path):
                print(f"Files for '{file_prefix}' already exist. Skipping...")
                return

            others_part = form_others(others, others_input)
            create_json_files(part_data, others_part, json_file, case_id, is_value)
            train_and_save_model(json_file, model_file, vectorizer_file, case_id)
            print(f"Creation of trained model for '{file_prefix}' is done")
        except Exception as e:
            print(f"Exception while processing '{file_prefix}' is: {e}")

    process_part(column_header, [row_header, context, values], f"{process}_{format}_column_headers")
    process_part(row_header, [column_header, context, values], f"{process}_{format}_row_headers")
    process_part(context, [row_header, column_header, values], f"{process}_{format}_context")
    process_part(values, [row_header, context, column_header], f"{process}_{format}_values", is_value=True)

    return True


------------------------------------------------------------------------------------------------------------------------------------------------

def get_template_extraction_values(ocr_data_all_got,ocr_raw_pages,process_trained_fields,fields,section_fields=False,common_section=False,sub_section=False,common_section_fields=[]):

    row_headers = process_trained_fields['row_headers']
    column_headers = process_trained_fields['column_headers']
    contexts = process_trained_fields['contexts']

    row_headers_t2 = process_trained_fields['row_headers_t2']
    column_headers_t2 = process_trained_fields['column_headers_t2']
    contexts_t2 = process_trained_fields['contexts_t2']

    # row_headers,column_headers,contexts=process_trained_fields['row_headers',{}],process_trained_fields['column_headers',{}],process_trained_fields['contexts',{}]

    if column_headers:
        column_headers=json.loads(column_headers)
    else:
        column_headers={}
    if row_headers:
        row_headers=json.loads(row_headers)
    else:
        row_headers={}
    if contexts:
        contexts=json.loads(contexts)
    else:
        contexts={}

    if column_headers_t2:
        column_headers_t2=json.loads(column_headers_t2)
    else:
        column_headers={}
    if row_headers_t2:
        row_headers_t2=json.loads(row_headers_t2)
    else:
        row_headers_t2={}
    if contexts_t2:
        contexts_t2=json.loads(contexts_t2)
    else:
        contexts_t2={}
    
    print(f" ########### all contexts_t2 got are  {contexts_t2}")
    print(f" ###########mall row_headers_t2 got are  {row_headers_t2}")
    print(f" ########### all column_headers_t2 got are  {column_headers_t2}")

    print(f" ########### all contexts got are  {contexts}")
    print(f" ########### all row_headers got are  {row_headers}")
    print(f" ###########all  column_headers got are  {column_headers}")
    
    extracted_fields={}
    fields_highlights={}

    for field in fields:

        if field in common_section_fields and sub_section:
            continue

        if field not in common_section_fields and common_section:
            continue 

        ocr_data_all=copy.deepcopy(ocr_data_all_got)
        print(F" #####################")
        print(F" #####################")
        print(F" #####################")
        print(F" ##################### fiels is {field}")
        print(F" #####################")
        print(F" #####################")
        print(F" #####################")

        extracted_fields[field]=''

        row_header_int=row_headers.get(field,[])
        column_header_int=column_headers.get(field,[])
        context_int=contexts.get(field,[])
        
        row_header_int_t2=[]
        if row_headers_t2:
            row_header_int_t2=row_headers_t2.get(field,[])
        column_header_int_t2=[]
        if column_headers_t2:
            column_header_int_t2=column_headers_t2.get(field,[])
        context_int_t2=[]
        if contexts_t2:
            context_int_t2=contexts_t2.get(field,[])

        print(f" ########### row_header_int_t2 got are  {row_header_int_t2}")
        print(f" ########### column_header_int_t2 got are  {column_header_int_t2}")
        print(f" ########### context_int_t2 got are  {context_int_t2}")


        if row_header_int_t2 and context_int_t2:
            row_header_int=row_header_int_t2
            column_header_int=column_header_int_t2
            context_int=context_int_t2
        
        print(f" ########### row_header_int got are  {row_header_int}")
        print(f" ########### column_header_int got are  {column_header_int}")
        print(f" ########### context_int got are  {context_int}")

        context_box={}
        if 'context_box' in context_int:
            context_box=context_int['context_box']
        row_box={}
        if 'row_box' in row_header_int:
            row_box=row_header_int['row_box']
        value_box={}
        if 'value_box' in row_header_int:
            value_box=row_header_int['value_box']

        # print(F" ##################### len of ocr_data_all is {len(ocr_data_all)}")
        finalised_headers=finalise_headers(row_header_int,column_header_int,context_int,copy.deepcopy(ocr_data_all_got),copy.deepcopy(ocr_raw_pages))

        column_header=finalised_headers['column_header']
        row_header=finalised_headers['row_header']
        context=finalised_headers['context']
        print(f" ########### finalised_headers got are  {finalised_headers}")
        if not row_header:
            continue
    
        for ocr_word in ocr_data_all_got:
            if not ocr_word:
                continue
            if ocr_word[0]['pg_no'] == row_header['pg_no']:
                value_page_ocr_data=ocr_word
        
        if row_header:
            possible_values_row_got,multi_line=finding_possible_values(row_header,row_header_int,value_page_ocr_data)
            print(f" ################ possible_values_row got are {possible_values_row_got}")

        print(f" ################ value_box got are {value_box}")
        print(f" ################ row_box got are {row_box}")
        print(f" ################ context_box got are {context_box}")
        if value_box:
            possible_values_row=[]
            for value in possible_values_row_got:
                if value_box['left']>=row_box['left'] and value['left']+10>=row_header['left']:
                    possible_values_row.append(value)
                else:
                    possible_values_row.append(value)
            
            trained_angle_rv=get_angle(value_box,row_box)
            trained_angle_cv=get_angle(value_box,context_box)

        else:
            possible_values_row=possible_values_row_got
        print(f" ################ possible_values_row got are {possible_values_row}")

        max_calculated_diff=10000
        predicted={}

        for value in possible_values_row:

            calculated_diff=0
            if row_header:
                value_row_diff_cal=calculate_distance(row_header,value)
                print(f'value is {value["word"]}')
                row_act_confidence=value_row_diff_cal
                row_base_diff=row_header_int['value_thr']
                row_conf=calculate_confidence(row_base_diff,row_act_confidence)
                print(f'row_act_confidence is {row_act_confidence}')
                print(f'row_base_diff is {row_base_diff}')
                print(f'row_conf is {row_conf}')
                # print(f"################ calculated_col_diff is  {row_header_int['value_thr']} for {value_row_diff_cal}")
                calculated_row_diff=abs(row_header_int['value_thr']-value_row_diff_cal)
                calculated_diff=calculated_diff+calculated_row_diff
                # print(f"################ calculated_diff is  {calculated_row_diff} for {value}")

            if context:
                
                column_act_confidence=calculate_value_distance(context,value)
                con_base_diff=context_int['value_thr']
                con_conf=calculate_cont_confidence(con_base_diff,column_act_confidence)
            
                print(f'value is {value["word"]}')
                print(f'column_confidence is {column_act_confidence}')
                print(f'con_base_diff is {con_base_diff}')
                print(f'con_conf is {con_conf}')

                value_con_diff_cal=calculate_value_distance(context,value)
                calculated_con_diff=abs(context_int['value_thr']-value_con_diff_cal)
                calculated_diff=calculated_diff+calculated_con_diff
                # print(f"################ calculated_diff is  {calculated_con_diff} for {value}")

            # print(f"################ calculated_diff is  {calculated_diff} for {value}")
            if max_calculated_diff>calculated_diff:

                angle_cv=get_angle(value,context)
                if value_box:
                    confidence = 1 - (min(abs(trained_angle_cv - angle_cv), 360 - abs(trained_angle_cv - angle_cv)) / 180)
                    confidence_percent_cv = round(confidence * 100, 2)
                    print(f"here angle_cv {angle_cv} and cal diff is {trained_angle_cv}")
                    print(f"here confidence_percent is {confidence_percent_cv}")

                angle_rv=get_angle(value,row_header)
                if value_box:
                    confidence = 1 - (min(abs(trained_angle_rv - angle_rv), 360 - abs(trained_angle_rv - angle_rv)) / 180)
                    confidence_percent_rv = round(confidence * 100, 2)
                    print(f"here angle_cv {angle_rv} and cal diff is {trained_angle_rv}")
                    print(f"here confidence_percent is {confidence_percent_rv}")
                # print(f"################ final predict is  {predicted}")
                # print(f"################ multi_line is  {multi_line}")
                try:
                    if value_box:
                        confindance= min([row_conf,con_conf,confidence_percent_rv,confidence_percent_cv])
                    else:
                        confindance= min([row_conf,con_conf])
                except Exception as e:
                    print("exception occured:::::{e}")

                print(f"here base_diff {calculated_diff} and cal diff is {row_conf,con_conf}a and {confindance}")
                max_calculated_diff=calculated_diff
                predicted=value

        if multi_line:
            predicted=find_y_values(predicted,value_page_ocr_data,True)

        print(f"################ final predict is  {predicted}")
        print('#################')
        print('\n')
        if predicted:
            extracted_fields[field]=predicted['word']
            fields_highlights[field]=from_highlights(predicted)     

    return extracted_fields,fields_highlights

-----------------------------------------------------------------------------------------------------------------------------------------------------------

def extract_table_header(ocr_data,top, table_headers, foot=False,table_header_text=[],header_check=False):
    """
    Extracts table data from OCR words starting from a predicted header. The function looks for the header
    and then traverses down, collecting rows of table data until it encounters an empty line, a large gap,
    or other stopping conditions.

    Args:
        words_ (list): List of dictionaries containing OCR data for words.
        div (str): Division identifier.
        seg (str): Segment identifier.

    Returns:
        list: Extracted table rows.
    """
    
    table_headers_line=line_wise_ocr_data(table_headers)
    table_line_words=[]
    for table_head_line in table_headers_line:
        temp=''
        for word in table_head_line:
            temp=temp+" "+word['word']
        table_line_words.append(temp)

    table_lines=[]
    print(F'table_headers is {table_line_words}')
    # Sort words by their "top" position to process lines vertically
    found=[]
    for table_line_word in table_line_words:
        temp_line=[]
        max_match=0
        for ocr in ocr_data:
            sorted_words = sorted(ocr, key=lambda x: x["top"])
            line_ocr=line_wise_ocr_data(sorted_words)
            for line in line_ocr:
                if line[0]['top']<top:
                    continue
                if foot:
                    line_words = [word["word"] for word in line]
                    line_words=" ".join(line_words)
                    line_words_temp=re.sub(r'[^a-zA-Z]', '', line_words)
                    table_line_word_temp=re.sub(r'[^a-zA-Z]', '', table_line_word)
                    matcher = SequenceMatcher(None, line_words_temp, table_line_word_temp)
                    similarity_ratio_col = matcher.ratio()
                    if similarity_ratio_col>max_match and similarity_ratio_col>0.65:
                        max_match=similarity_ratio_col
                        temp_line=line
                        print(f"table_lineis {line_words} and table header is {table_line_word} and {similarity_ratio_col}")
                else:
                    line_words = [word["word"] for word in line]
                    line_words=" ".join(line_words)
                    matcher = SequenceMatcher(None, line_words, table_line_word)
                    similarity_ratio_col = matcher.ratio()
                    if similarity_ratio_col>max_match and similarity_ratio_col>0.65:
                        max_match=similarity_ratio_col
                        temp_line=line
                        print(f"table_lineis {line_words} and table header is {table_line_word} and {similarity_ratio_col}")
            print(f"temp_line got for this page is {temp_line}")
            if temp_line:
                table_lines.extend(temp_line)
        if temp_line:
            found.append(table_line_word)  

    print(F'table_line is {table_lines}')
    if not table_lines or len(found)!=len(table_line_words):
        table_lines_=detect_table_header_2(table_headers,ocr_data)
        if not table_lines and not table_lines_:
            print("No table header detected.")
            if header_check:
                return []
            return [],[]
        elif table_lines_:
            table_lines=table_lines_

    table_header_box=combine_dicts(table_lines)

    if not table_header_box:
        return [],[] 

    final_line=[]
    for ocr in ocr_data:
        sorted_words = sorted(ocr, key=lambda x: x["top"])
        line_ocr=line_wise_ocr_data(sorted_words)
        for line in line_ocr:
            line_box=combine_dicts(line)
            if line_box and table_header_box['top']<=line_box['top']<=table_header_box['bottom'] and line_box['pg_no'] == table_header_box['pg_no']:
                print(F'final table lines are is {line_box}')
                final_line.extend(line)

    if header_check:
        return final_line
    
    new_lines=[]
    for word in final_line:
        new_lines.append(word)

    table_lines=new_lines

    print(F'table_header_text is {table_header_text}')

    whole_table_box=combine_dicts(new_lines)
    header_page=whole_table_box['pg_no']

    if table_header_text:
        new_lines_=[]
        for page in ocr_data:
            if page and page[0]['pg_no'] == header_page:
                for word in page:
                    if whole_table_box['top']-100<=word['top'] and  whole_table_box['bottom']+100>=word['bottom']:
                        # print(f'words is checking here {word}')
                        new_lines_.append(word)

        if new_lines_:
            table_lines=new_lines_

    print(F'table_header_text is {combine_dicts(table_lines)}')

    if not table_header_text:
        headers=group_words_into_columns(table_lines, col_threshold=5)
    else:
        table_header_text=list(table_header_text)
        print(F'table_header_text is {table_header_text}')
        sorted_words = sorted(table_header_text, key=lambda x: len(x.split()), reverse=True)
        headers=[]
        for header in sorted_words:
            words=[word for word in header.split() if re.sub(r'[^a-zA-Z%#]', '', word)]
            found_header=find_accurate_table_header([table_lines],words)
            new_table_lines=[]
            for word in table_lines:
                if found_header and (found_header['left']<=word['left'] and word['right']<=found_header['right']):
                    pass
                else:
                    new_table_lines.append(word)
            table_lines=new_table_lines
            print(f'found_header is {found_header} for the header is {header}')
            headers.append(found_header)

    final_head=[]
    for head in headers:
        if head:
            final_head.append(head)

    return final_head,table_line_words

------------------------------------------------------------------------------------------------------------------------------------------------

def extract_remarks(headers,footers,ocr_word_all):
    try:
        headers=headers['ocrAreas']
    except:
        headers=headers
    footers=[]

    all_head_identifiers=[]
    for head in headers:
        all_head_identifiers.append(combine_dicts(head))
    # print(f" ################# all_head_identifiers",all_head_identifiers)

    base_head={}
    if all_head_identifiers:
        base_head=max(all_head_identifiers, key=lambda w: w["top"])
    # print(f" ################# base_head",base_head)

    all_foot_identifiers=[]
    for foot in footers:
        all_foot_identifiers.append(combine_dicts(foot))
    # print(f" ################# all_foot_identifiers",all_foot_identifiers)

    base_foot={}
    if all_foot_identifiers:
        base_foot=min(all_foot_identifiers, key=lambda w: w["top"])
    # print(f" ################# base_foot",base_foot)

    if not base_head:
        return {},{}

    remarks_ocr_data_temp=[]
    matched_word=''
    end_matcher=False
    start_matcher=False
    for page in ocr_word_all:
        sorted_words = sorted(page, key=lambda x: (x["top"]))
        word_lines=line_wise_ocr_data(sorted_words)
        current_index=-1
        # print(f'############### word_lines for oage {word_lines[0]} are',word_lines)
        for line in word_lines:
            # print(f'############### line is',line)
            current_index=current_index+1
            for word in line:
                base_identifier_word=re.sub(r'[^a-zA-Z ]', '', base_head['word'])
                if base_identifier_word and not start_matcher:
                    start_matcher = is_fuzzy_subsequence(base_identifier_word, word['word'])
                
                    if start_matcher:
                        matched_word=word
                        if len(all_head_identifiers)>1:
                            words=[]
                            valid_start=True
                            print(f'############### word_lines next lines {current_index} is',word_lines[current_index-4:current_index+1])
                            for word_ in word_lines[current_index-4:current_index+1]:
                                for wo in word_:
                                    words.append(wo['word'])

                            if not words:
                                for word_ in word_lines[current_index:current_index+3]:
                                    for wo in word_:
                                        words.append(wo['word'])
                            print(f'############### here words to consider for nextline',words)

                            for ident in all_head_identifiers:
                                if base_head['word'] != ident['word']:
                                    if not is_word_present(ident['word'], words, threshold=0.95):
                                        print(f'############### identifier not found in this line and the ident is',ident)
                                        valid_start=False
                                        break
                            if not valid_start:
                                start_matcher=False
                                continue

                    if start_matcher:
                        print(f'first line strated is {line}')
                        # temp_line=[]
                        # for word_ in line:
                        #     if word == word_:
                        #         continue
                        #     if word not in temp_line:
                        #         temp_line.append(word)
                        if 'Note' not in matched_word['word'].split():
                            line.remove(matched_word)  
                            
                        print(f'first line strated aftere remove start is {line}')
                        start_header=matched_word
                        if line:
                            if line not in remarks_ocr_data_temp:
                                remarks_ocr_data_temp.append(line)
                        break

                if start_matcher and base_foot:
                    end_matcher = is_fuzzy_subsequence(base_foot['word'], word['word'])
                    break

                if start_matcher:
                    if line not in remarks_ocr_data_temp:
                        remarks_ocr_data_temp.append(line)
                    break

            if end_matcher:
                break

    # print(f'############### remarks_ocr_data_temp is',remarks_ocr_data_temp)

    remarks_ocr_data=remarks_ocr_data_temp
    # for temp_line in remarks_ocr_data_temp:
    #     rmk_line=combine_dicts(temp_line)
    #     if check_remark_row(rmk_line['word']):
    #         remarks_ocr_data.append(temp_line)

    # print(f'############### remarks_ocr_data is',remarks_ocr_data)

    for lst in remarks_ocr_data:
        lst.sort(key=lambda x: x["top"])

    if remarks_ocr_data:
        # Sort the outer list based on the smallest "top" value of each inner list
        remarks_ocr_data=sorted(remarks_ocr_data, key=lambda group: (group[0]['pg_no'], group[0]['top']))

    print(f'############### remarks_ocr_data is',remarks_ocr_data)

    Remarks=[]
    start_word=[]
    other_word=[]
    has_start=False
    i=0
    for i in  range(len(remarks_ocr_data)):
        remark_line=sorted(remarks_ocr_data[i], key=lambda x: (x["left"]))
        print(f'############### remark_line is',remark_line)
        for j in range(len(remark_line)):

            if j == len(remark_line)-1 and len(remark_line)>1:
                break
            
            words = remark_line[j]['word']

            if not is_remark_code_present(remark_line[j]['word']):
                continue
            
            has_start=True
            start_word=[remark_line[j]]
            if len(remark_line) == 1:
                other_word=None
            else:
                other_word=remark_line[j+1]
            print(f'############### start_word is',start_word)
            print(f'############### other_word is',other_word)
            break
        if start_word:
            break

        if i>3 and not start_word:
            start_word=remarks_ocr_data[0]
            i=0
            break
    
    if start_word:
        final_remarks={}
        final_high={}
        Remarks.append(start_word)
        print(f'############### Remarks is',Remarks)
        if not other_word:
            flag_stop=False
            prev_bootom=start_word[0]
            for remark_line in remarks_ocr_data[i+1:]:
                remark_line_box=combine_dicts(remark_line)
                for word in remark_line:
                    if start_word[0]['pg_no']!=word['pg_no']:
                        prev_bootom['bottom']=0
                    print(f'############### start_word',start_word[0],word)

                    if prev_bootom['bottom']<word['top']:

                        if abs(prev_bootom['bottom']-word['top'])>50:
                            if not is_remark_code_present(remark_line_box['word']):
                                continue

                        if remark_line not in Remarks:
                            prev_bootom=word
                            Remarks.append(remark_line)

            print(f'############### Remarks is',Remarks)
            
            te=0
            sorted_line = sorted(Remarks[0], key=lambda x: (x["left"]))
            combine_line=combine_dicts(sorted_line)
            prev_length=combine_line['right']-combine_line['left']
            temp_remark=[combine_dicts(Remarks[0])]

            print(f'############### temp_remark is',temp_remark)
            
            for re_line in Remarks[1:]:

                sorted_line = sorted(re_line, key=lambda x: (x["left"]))
                current_line=combine_dicts(sorted_line)
                current_length=current_line['right']-current_line['left']

                print(f'############### current_line is',current_line)
                print(f'############### prev_length is',prev_length)
                print(f'############### current_length is',current_length)

                check_start=False
                if has_start:
                    check_start=is_remark_code_present(current_line['word'])

                if check_start:
                    lines=line_wise_ocr_data(temp_remark)
                    all_words=[]
                    for line in lines:
                        # line[-1]['word']=line[-1]['word']+'//n'
                        all_words.extend(line)
                    final_remarks[str(te+1)+'**']=combine_dicts(all_words)['word']
                    final_high[str(te+1)+'**']=from_highlights(combine_dicts(temp_remark))
                    temp_remark=[current_line]
                    te=te+1
                else:
                    temp_remark.append(current_line)

                prev_length=current_length
                print(f'############### temp_remark is',temp_remark)

            if temp_remark:
                lines=line_wise_ocr_data(temp_remark)
                all_words=[]
                for line in lines:
                    # line[-1]['word']=line[-1]['word']+'//n'
                    all_words.extend(line)
                final_remarks[str(te+1)+'**']=combine_dicts(all_words)['word']
                final_high[str(te+1)+'**']=from_highlights(combine_dicts(temp_remark))

        elif other_word:
            try:
                prev_bootom = start_word['bottom']
                prev_page = start_word['pg_no']
            except Exception as e:
                try:
                    start_word = start_word[0] 
                    prev_bootom = start_word['bottom']
                    prev_page = start_word['pg_no']
                except Exception as e:
                    print(f"the exception is::::{e}")  # or handle differently if needed

            # prev_bootom=start_word['bottom']
            prev_page=start_word['pg_no']
            prev_bootom = start_word['bottom']
            break_flag=False
            for remark_line in remarks_ocr_data[i+1:]:
                if prev_page != remark_line[0]['pg_no']:
                    prev_bootom=remark_line[0]['top']

                remark_line=sorted(remark_line, key=lambda x: x["left"])
                print(f'############### start_word checking in ',remark_line)

                for word in remark_line:

                    if word['height']>20:
                        continue

                    if start_word['right']+5>word['left']>start_word['left']-5 or start_word['right']+5>word['right']>start_word['left']-5 or start_word['right']+5>(word['left']+word['right'])/2>start_word['left']-5:
                        temP_word = word['word'].split()  # Step 1: split into words
                        cleaned_words = [re.sub(r'[^a-zA-Z0-9]', '', word_) for word_ in temP_word if re.sub(r'[^a-zA-Z0-9]', '', word_)]

                        if is_remark_code_present(word['word']):
                            print(f'############### start_word found in ',word)
                            if len(cleaned_words)>1:
                                temp=copy.deepcopy(word)
                                temp['left']=0
                                temp['right']=0
                                temp['word']=cleaned_words[0]
                                print(f'############### modified strat in ',temp)
                                Remarks.append(temp)
                            else:
                                Remarks.append(word)
                            break
                        # elif len(cleaned_words) == 1 and word not in Remarks and (not re.sub(r'[^a-zA-Z]', '', cleaned_words[0]) or cleaned_words[0].isupper()):
                        #     Remarks.append(word)
                    elif word['right']+5>start_word['left']>word['left']-5 or word['right']+5>start_word['right']>word['left']-5 or word['right']+5>(start_word['left']+start_word['right'])/2>word['left']-5:
                        temP_word = word['word'].split()  # Step 1: split into words
                        cleaned_words = [re.sub(r'[^a-zA-Z0-9]', '', word_) for word_ in temP_word if re.sub(r'[^a-zA-Z0-9]', '', word_)]

                        if is_remark_code_present(word['word']):
                            print(f'############### start_word found in ',word)
                            if len(cleaned_words)>1:
                                temp=copy.deepcopy(word)
                                temp['left']=0
                                temp['right']=0
                                temp['word']=cleaned_words[0]
                                print(f'############### modified strat in ',temp)
                                Remarks.append(temp)
                            else:
                                Remarks.append(word)
                            break
                        # elif len(cleaned_words) == 1 and word not in Remarks and (not re.sub(r'[^a-zA-Z]', '', cleaned_words[0]) or cleaned_words[0].isupper()):
                        #     Remarks.append(word)
                    elif word['left']<start_word['left']:
                        temP_word = word['word'].split()  # Step 1: split into words
                        cleaned_words = [re.sub(r'[^a-zA-Z0-9]', '', word_) for word_ in temP_word if re.sub(r'[^a-zA-Z0-9]', '', word_)]

                        if is_remark_code_present(word['word']):
                            print(f'############### start_word found in ',word)
                            if len(cleaned_words)>1:
                                temp=copy.deepcopy(word)
                                temp['left']=0
                                temp['right']=0
                                temp['word']=cleaned_words[0]
                                print(f'############### modified strat in ',temp)
                                Remarks.append(temp)
                            else:
                                Remarks.append(word)
                            break

                prev_bootom=word['bottom']
                prev_page=word['pg_no']

                if break_flag:
                    break
        
            # print(f'############### Remarks is',Remarks)
            print(f'############### Remarks is', Remarks)

            remarks_code = {}
            if Remarks:
                last_bottom = next((r for r in Remarks[:2] if isinstance(r, dict) and 'bottom' in r), None)
                # last_bottom = next((r for r in Remarks[:2] if isinstance(r, dict) and 'bottom' in r), None)
                for i in range(len(Remarks)):
                    current = Remarks[i][0] if isinstance(Remarks[i], list) else Remarks[i]
                    current_top = current.get('top')
                    current_bottom = current.get('bottom')
                    current_page = current.get('pg_no')

                    if len(Remarks) - 1 == i:
                        next_top = 1000
                    else:
                        next_item = Remarks[i + 1][0] if isinstance(Remarks[i + 1], list) else Remarks[i + 1]
                        if next_item.get('pg_no') == current_page:
                            next_top = next_item.get('top', 1000)
                        else:
                            next_top = 1000

                    if isinstance(last_bottom, dict) and last_bottom.get('bottom', 0) > current_top:
                        last_bottom = Remarks[i]

                    print(f'############### current_top is', current_top)
                    print(f'############### current is', current)
                    print(f'############### next_top is', next_top)
                    print(f'############### last_bottom is', last_bottom)

                    code_line = []

                    for remark_data in remarks_ocr_data:

                        print(f'############### lone is',remark_data)

                        if current_page != remark_data[0]['pg_no']:
                            continue

                        top=max(remark_data, key=lambda w: w["top"])
                        left=max(remark_data, key=lambda w: w["left"])

                        # print(f'############### top is',top)
                        if (last_bottom and abs(top['top'] - (last_bottom[0]['bottom'] if isinstance(last_bottom, list) else last_bottom['bottom']) ) > 10 
                            and top['top'] > (last_bottom[0]['bottom'] if isinstance(last_bottom, list) else last_bottom['bottom']) 
                            and code_line):
                            break
  
                        if (last_bottom and (last_bottom[0]['left'] if isinstance(last_bottom, list) else last_bottom['left']) > left['left'] 
                            and code_line):
                            break

                        code_line=[]

                        sorted_data = sorted(remark_data, key=lambda x: (x["left"]))
                        key = Remarks[i][0]['word'] if isinstance(Remarks[i], list) else Remarks[i]['word']
                        if next_top>top['top']>=current_top:
                            for word in sorted_data:
                                if word ['word']== key:
                                    continue
                                code_line.append(word)
                                last_bottom=sorted_data[0]

                        if code_line:
                            if key not in remarks_code:
                                remarks_code[key] = []
                            remarks_code[key].append(combine_dicts(code_line))

                        print(f'############### code_line is',code_line)

                    print(f'############### remarks_code is',remarks_code)

                for remark_code,value in  remarks_code.items(): 
                    temp=combine_dicts(value)   
                    final_remarks[remark_code]=temp['word']
                    final_high[remark_code]=from_highlights(temp)
 
        try:    
            final_high['Remark_default']=from_highlights(start_header)
        except:
            pass

        return final_remarks,final_high
    else:
        return {}, {}

-----------------------------------------------------------------------------------------------------------------------------
def predict_sub_templates(section_identifier,ocr_word_all,ocr_data_all,section_header,process_trained_fields):

    section_heads=[]
    section_format=[]
    if section_header:
        section_heads=section_header['identifiers']
        section_format=section_header['formats']

    try:
        print(f" ################# identifiers['section_identifiers']",section_identifier)
        if not section_identifier:
            return None,None,None,None
        
        start=section_identifier[0]
        # print(f" ################# start",start)
        # end=section_identifier[1]
        try:
            end=section_identifier[1]
        except:
            end=[]
        # print(f" ################# end",end)


        all_identifiers=[]
        other_identifers={}
        for identifiers in start:
            if not identifiers:
                continue
            lines_identifiers=line_wise_ocr_data(identifiers)
            temp_ident=combine_dicts(lines_identifiers[0])
            all_identifiers.append(temp_ident)
            other_identifers[temp_ident['word']]=[]
            for other_ident in lines_identifiers[1:]:
                other_identifers[temp_ident['word']].append(combine_dicts(other_ident)['word'])
        print(f" ################# all_identifiers",all_identifiers)
        # print(f"other identifiers got are {other_identifers}")

        base_identifier=min(all_identifiers, key=lambda w: w["top"])
        print(f" ################# base_identifier",base_identifier)

        all_end_identifiers=[]
        if end:
            for identifiers in end:
                if identifiers:
                    all_end_identifiers.append(combine_dicts(identifiers))
            print(f" ################# all_end_identifiers",all_end_identifiers)

        base_end_identifier={}
        if all_end_identifiers:
            base_end_identifier=max(all_end_identifiers, key=lambda w: w["top"])
            print(f" ################# base_end_identifier",base_end_identifier)

        # Compute distances
        distances = {}
        for word in all_end_identifiers:
            if word != base_identifier and word:
                dist = base_identifier['right']-word['left']
                distances[word["word"]]= dist
        #         print(f" ################# word and dist",word ,dist)
        # print(f" ################ distances",distances)

    except Exception as e:
        print(f"here we have an exception {e}")
        all_identifiers=[]
        other_identifers={}
        base_end_identifier={}
        all_end_identifiers=[]
        for identifiers in section_identifier:
            all_identifiers.append(combine_dicts(identifiers))
        print(f" ################# all_identifiers",all_identifiers)

        base_identifier=min(all_identifiers, key=lambda w: w["top"])
        print(f" ################# base_identifier",base_identifier)

        # Compute distances
        distances = {}
        for word in all_identifiers:
            if word != base_identifier:
                dist = base_identifier['right']-word['left']
                distances[word["word"]]= dist
                print(f" ################# word and dist",word ,dist)
        print(f" ################ distances",distances)

    found_flag=False
    cordinates=[]
    end_point={}

    Claim_countinuation_word=['CONTINUED ON NEXT PAGE']

    try:
        start_page=ocr_word_all[0][0]['pg_no']
    except:
        for page in ocr_word_all:
            for words in page:
                for word in words:
                    start_page=word['pg_no']
    skip_count=0

    for page in ocr_word_all:
        sorted_words = sorted(page, key=lambda x: (x["top"]))
        word_lines=line_wise_ocr_data(sorted_words)
        current_index=-1

        print(f'################ we are at validating word {page[0]["pg_no"]}')

        for line in word_lines:
            current_index=current_index+1

            line_words = [word["word"] for word in line]
            line_words=' '.join(line_words)
            for wo in Claim_countinuation_word:
                if is_fuzzy_subsequence(wo, line_words):
                    skip_count=0
                    break

            for word in line:
                cleaned_word=re.sub(r'[^a-zA-Z]', '', word['word'])
                base_identifier_word=re.sub(r'[^a-zA-Z]', '', base_identifier['word'])
                if base_identifier_word:

                    if end_point and ((end_point['pg_no'] > word['pg_no']) or (end_point['pg_no'] == word['pg_no'] and word['top'] < end_point['bottom'])):
                        continue
                    
                    start_matcher = is_fuzzy_subsequence(base_identifier['word'], word['word'])
                    print(f'################ start_matcher word {word["word"]} is {start_matcher}')

                    similarity_ratio_con_end=0
                    end_matcher=False
                    if base_end_identifier:
                        end_matcher = is_fuzzy_subsequence(base_end_identifier['word'], word['word'])

                    if skip_count >0 and (start_matcher or end_matcher):
                        start_matcher=False
                        end_matcher=False
                        skip_count=skip_count-1

                    if start_matcher:

                        if len(all_identifiers)>1:
                            words=[]
                            valid_start=True
                            for word_ in word_lines[current_index:current_index+5]:
                                for wo in word_:
                                    words.extend(wo['word'].split())
                            print(f'############### here words to consider for nextline',words)

                            for ident in all_identifiers:
                                if base_identifier['word'] != ident['word']:
                                    temp_ids=ident['word'].split()
                                    for temp_id in temp_ids:
                                        if not is_word_present(temp_id, words, threshold=0.95):
                                            print(f'############### identifier not found in this line and the ident is',ident)
                                            valid_start=False
                                            break
                            
                            if not valid_start:
                                continue

                        if cordinates and not end_point and len(cordinates[-1])<3:
                            print(f'############### another line is found but append this start as last end',word)
                            cordinates[-1].extend([word['pg_no'],word['top']])

                        valid=True
                        if other_identifers and len(other_identifers[base_identifier['word']])>0:
                            words=[]
                            for word_ in word_lines[current_index:current_index+5]:
                                for wo in word_:
                                    words.append(wo['word'])
                            print(f'############### here words to consider for nextline',words)
                            for ident in other_identifers[base_identifier['word']]:
                                if not is_word_present(ident, words, threshold=0.95):
                                    print(f'############### identifier not found in this line and the ident is',ident)
                                    valid=False
                                    break

                        if not valid:
                            continue

                        end_point=valid_identifier(ocr_word_all,distances,word)
                        print(f'################ sub template is found at line',word ,end_point)

                        if end_point and len(all_end_identifiers)>1:
                            words=[]
                            valid_end=True
                            ind=0
                            for page_end in ocr_word_all:
                                if end_point['pg_no']== page_end[0]['pg_no']:
                                    word_lines_ed=line_wise_ocr_data(page_end)
                                    for word_ in word_lines_ed:
                                        if ind>5:
                                            break
                                        if end_point['top']<=word_[0]['top']:
                                            for wo in word_:
                                                words.append(wo['word'])
                                            ind=ind+1
                            print(f'############### here words to consider for 1',words)

                            for ident in all_end_identifiers:
                                if base_end_identifier['word'] != ident['word']:
                                    if not is_word_present(ident['word'], words, threshold=0.95):
                                        print(f'############### identifier not found in this line and the ident is',ident)
                                        valid_end=False
                                        break

                            if valid_end:
                                if end_point:
                                    print(f'################ end_point',end_point,'for',word)
                                    cordinates.append([word['pg_no'],word['top'],end_point['pg_no'],end_point['bottom']])
                                
                        elif end_point:
                            print(f'################ end_point',end_point,'for',word)
                            cordinates.append([word['pg_no'],word['top'],end_point['pg_no'],end_point['bottom']])
                                
                        elif not end_point:
                            print(f'################ no end_point',end_point,'for',word)
                            cordinates.append([word['pg_no'],word['top']])
                            print(f'################ cordinates',cordinates)

                    elif end_matcher:

                        print(f'############## validatig end identifier for nextline')

                        words=[]
                        valid_end=True
                        for word_ in word_lines[current_index:current_index+4]:
                            for wo in word_:
                                words.extend(wo['word'].split())
                        print(f'############### here words to consider for nextline',words)

                        for ident in all_end_identifiers:
                            if base_end_identifier['word'] != ident['word']:
                                base_end=ident['word'].split()
                                for end_wo in base_end:
                                    if not is_word_present(end_wo, words, threshold=0.95):
                                        print(f'############### identifier not found in this line and the ident is',ident)
                                        valid_end=False
                                        break

                        if valid_end:
                            if cordinates:
                                if len(cordinates[-1])<3:
                                    print(f'############### another line is found but append this start as last end',word)
                                    cordinates[-1].extend([word['pg_no'],word['bottom']])
                                    continue

                                print(f'################ direct end_point',end_point,'for',word)
                                cordinates.append([cordinates[-1][2],cordinates[-1][3]+1,word['pg_no'],word['bottom']])
                                print(f'################ cordinates',cordinates)
                            else:
                                cordinates.append([start_page,0,word['pg_no'],word['bottom']])
                                print(f'################ cordinates',cordinates)

    last_page=sorted(ocr_data_all[-1], key=lambda x: (x["top"]))
    if cordinates and len(cordinates[-1])<4:
        # print(f'############### we have didnt find any end point in the last so appending last wrd of last page',last_page[-1])
        cordinates[-1].extend([last_page[-1]['pg_no'],last_page[-1]['bottom']])

    print(f'cordinates',cordinates)

    print(f'section ocr satrting here')
    all_sections=[]
    index=-1
    all_headers=[] 
    pre_claim=''
    new_cord=[]
    for cordinate in cordinates:
        index=index+1
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_word_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word_line=sorted(word_line, key=lambda x: (x["pg_no"], x["top"]))
                word=word_line[0]
                if word['bottom'] > end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top']+5 >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    # print(f"start word is {word}")
                    section[word['pg_no']].extend(word_line)
            if stop:
                break
        print(f'one section ending here',section.keys())
        if section_heads:
            section_format_identification=section_format

            if index==0:
                for head in section_heads:
                    detected_header_got=extract_section_header(ocr_pages,head,start_pg)
                    detected_header=copy.deepcopy(detected_header_got)
                    if detected_header:
                        all_headers.extend(detected_header)
                print(f'all_headers here',all_headers)
                if all_headers:
                    temp_section=get_filtered_section(section,section_format_identification)

                    if temp_section:
                        section=temp_section

                    print(f'index 0 here',detected_header)
                    for he in all_headers:
                        if he in section[start_pg]:
                            section[start_pg].remove(he)

                    header_box=combine_dicts(all_headers)
                    print(f'header_box here',header_box)

                    # print(f'section[word[pg_no]] here',section[word['pg_no']])
                    actual_start=combine_dicts(section[start_pg])
                    print(f'actual_start here',actual_start)
                    actual_start=actual_start['top']
                    # print(f'actual_start here',actual_start)
                    second_header_diff=header_box['bottom']-actual_start
                    # print(f'second_header_diff here',second_header_diff)
                    
                    print(f'adding to section {section}')
                    for head in all_headers:
                        print(f'adding to header {head}')
                        if head['pg_no'] in section:
                            print(f'adding to header {head}')
                            section[head['pg_no']].extend(all_headers)
                            break

            else:

                if section and all_headers:
                    header_box=[]

                    temp_section=get_filtered_section(section,section_format_identification)
                    if temp_section:
                        section=temp_section
                        temp_start_pg=list(temp_section.keys())[0]
                    else:
                        temp_start_pg=start_pg

                    temp_headers=copy.deepcopy(all_headers)
                    header_box=combine_dicts(temp_headers)
                    
                    if section[temp_start_pg]:
                        start_cord=combine_dicts(section[temp_start_pg])
                    else:
                        start_cord=combine_dicts(section[start_pg])
                    print(f'start_cord here',start_cord)

                    if start_cord:
                        start_cord=start_cord['top']
                        current_header_diff=header_box['bottom']-start_cord
                        print(f'current_header_diff here',current_header_diff)
                        print(f'second_header_diff here',second_header_diff)
                        overall_diff=current_header_diff-second_header_diff
                        print(f'overall_diff here',overall_diff)
                        
                        for head in temp_headers:
                            if head['pg_no']!= temp_start_pg:
                                head['pg_no']=temp_start_pg
                            head['top']=head['top']-overall_diff
                            head['bottom']=head['bottom']-overall_diff

                        # print(f'section_headers after modfication here',detected_header)
                        print(f'adding to section {section}')
                        for head in temp_headers:
                            print(f'adding to header {head}')
                            if head['pg_no'] in section:
                                section[head['pg_no']].extend(temp_headers)
                                break

        print(f' -----> section here is ',section)
        
        # try:
        claim_id=check_claim(list(section.values()),process_trained_fields)
        # except Exception as e:
        #     print(f'here we have an exception is {e}')
        #     claim_id=''
        print(f'claim_id got is {claim_id}')
        print(f'pre_claim got is {pre_claim}')
        if pre_claim and pre_claim ==  claim_id:
            print(f'claim_id got is {all_sections[-1]}')
            print(f'pre_claim got is {section}')
            pre_claim=claim_id
            combined = {}
            for k in set(all_sections[-1]) | set(section):   # union of keys
                combined[k] = all_sections[-1].get(k, []) + section.get(k, [])
            all_sections[-1]=combined
            new_cord[-1][2]=cordinate[2]
            new_cord[-1][3]=cordinate[3]
        else:
            pre_claim=claim_id
            all_sections.append(section)
            new_cord.append(cordinate)

    print(f'New cords formed are {new_cord}')
    cordinates=new_cord

    reamark_cordinates=[]
    for i in range(len(cordinates)):

        current=cordinates[i]
        if i == len(cordinates)-1:
            next_=[last_page[-1]['pg_no'],last_page[-1]['bottom']]
        else:
            next_=cordinates[i+1]
        merged = current[:2] + next_[:2] 
        reamark_cordinates.append(merged)

    remarks_section_ocr=[]
    for cordinate in reamark_cordinates:
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_word_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word=word_line[0]
                if word['top'] >= end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top'] >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    section[word['pg_no']].extend(word_line)
            if stop:
                break
        # print(f'one section ending here',section.keys())
        for head in section_heads:
            detected_header=extract_section_header(ocr_pages,head,start_pg)
            # print(f'section_headers here',detected_header)
            for head in detected_header:
                if head['pg_no'] in section:
                    section[head['pg_no']].extend(detected_header)
                    break
        remarks_section_ocr.append(section)


    print(f'section ocr 2 satrting here')
    all_headers=[]  
    all_ocr_sections=[]
    index=-1
    for cordinate in cordinates:
        index=index+1
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_data_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            if not page:
                continue
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word_line=sorted(word_line, key=lambda x: (x["pg_no"], x["top"]))
                word=word_line[0]
                if word['bottom'] > end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top']+5 >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    # print(f"start word is {word}")
                    section[word['pg_no']].extend(word_line)
            if stop:
                break
        # print(f'one section ending here',section.keys())
        if section_heads:
            section_format_identification=section_format

            if index==0:
                for head in section_heads:
                    detected_header_got=extract_section_header(ocr_pages,head,start_pg)
                    detected_header=copy.deepcopy(detected_header_got)
                    if detected_header:
                        all_headers.extend(detected_header)
                print(f'all_headers here',all_headers)
                if all_headers:
                    temp_section=get_filtered_section(section,section_format_identification)

                    if temp_section:
                        section=temp_section

                    print(f'index 0 here',detected_header)
                    for he in all_headers:
                        if he in section[start_pg]:
                            section[start_pg].remove(he)

                    header_box=combine_dicts(all_headers)
                    print(f'header_box here',header_box)

                    # print(f'section[word[pg_no]] here',section[word['pg_no']])
                    actual_start=combine_dicts(section[start_pg])
                    print(f'actual_start here',actual_start)
                    actual_start=actual_start['top']
                    # print(f'actual_start here',actual_start)
                    second_header_diff=header_box['bottom']-actual_start
                    # print(f'second_header_diff here',second_header_diff)
                    
                    for head in all_headers:
                        if head['pg_no'] in section:
                            section[head['pg_no']].extend(all_headers)
                            break

            else:
            
                if section and all_headers:
                    header_box=[]

                    temp_section=get_filtered_section(section,section_format_identification)
                    if temp_section:
                        section=temp_section
                        temp_start_pg=list(temp_section.keys())[0]
                    else:
                        temp_start_pg=start_pg

                    temp_headers=copy.deepcopy(all_headers)
                    header_box=combine_dicts(temp_headers)
                    if section[temp_start_pg]:
                        start_cord=combine_dicts(section[temp_start_pg])
                    else:
                        start_cord=combine_dicts(section[start_pg])
                    print(f'start_cord here',start_cord)

                    if start_cord:
                        start_cord=start_cord['top']
                        current_header_diff=header_box['bottom']-start_cord
                        print(f'current_header_diff here',current_header_diff)
                        print(f'second_header_diff here',second_header_diff)
                        overall_diff=current_header_diff-second_header_diff
                        print(f'overall_diff here',overall_diff)
                        
                        for head in temp_headers:
                            if head['pg_no']!= temp_start_pg:
                                head['pg_no']=temp_start_pg
                            head['top']=head['top']-overall_diff
                            head['bottom']=head['bottom']-overall_diff

                        # print(f'section_headers after modfication here',detected_header)
                        for head in temp_headers:
                            if head['pg_no'] in section:
                                section[head['pg_no']].extend(temp_headers)
                                break
                        
        all_ocr_sections.append(section)
                
    return all_sections,cordinates,all_ocr_sections,remarks_section_ocr

-----------------------------------------------------------------------------------------------------------------------------------------------

def predict_sub_sub_templates(section_identifier,ocr_word_all,ocr_data_all):
    
    print(f" ################# identifiers['section_identifiers']",section_identifier)
    if not section_identifier:
        return None,None,None,None
    
    start=section_identifier

    all_identifiers=[]
    other_identifers={}
    for identifiers in start:
        if not identifiers:
            continue
        lines_identifiers=line_wise_ocr_data(identifiers)
        temp_ident=combine_dicts(lines_identifiers[0])
        all_identifiers.append(temp_ident)
        other_identifers[temp_ident['word']]=[]
        for other_ident in lines_identifiers[1:]:
            other_identifers[temp_ident['word']].append(combine_dicts(other_ident)['word'])
    print(f" ################# all_identifiers",all_identifiers)

    base_identifier=min(all_identifiers, key=lambda w: w["top"])
    print(f" ################# base_identifier",base_identifier)

    cordinates=[]
    end_point={}

    for page in ocr_word_all:
        sorted_words = sorted(page, key=lambda x: (x["top"]))
        word_lines=line_wise_ocr_data(sorted_words)
        current_index=-1
        for line in word_lines:
            current_index=current_index+1
            for word in line:
                base_identifier_word=re.sub(r'[^a-zA-Z]', '', base_identifier['word'])
                if base_identifier_word:

                    if end_point and ((end_point['pg_no'] > word['pg_no']) or (end_point['pg_no'] == word['pg_no'] and word['top'] < end_point['bottom'])):
                        continue
                    
                    # start_matcher = is_fuzzy_subsequence(base_identifier['word'], word['word'])

                    match_ratio = SequenceMatcher(None, word['word'], base_identifier['word']).ratio()
                    
                    if match_ratio >= 0.85:
                        start_matcher=True
                    else:
                        start_matcher=False

                    if start_matcher:

                        if len(all_identifiers)>1:
                            words=[]
                            valid_start=True
                            for word_ in word_lines[current_index:current_index+4]:
                                for wo in word_:
                                    words.extend(wo['word'].split())
                            print(f'############### here words to consider for nextline',words)

                            for ident in all_identifiers:
                                if base_identifier['word'] != ident['word']:
                                    temp_ids=ident['word'].split()
                                    for temp_id in temp_ids:
                                        if not is_word_present(temp_id, words, threshold=0.95):
                                            print(f'############### identifier not found in this line and the ident is',ident)
                                            valid_start=False
                                            break
                            
                            if not valid_start:
                                continue

                        if cordinates and not end_point and len(cordinates[-1])<3:
                            print(f'############### another line is found but append this start as last end',word)
                            cordinates[-1].extend([word['pg_no'],word['top']])

                        valid=True
                        if other_identifers and len(other_identifers[base_identifier['word']])>0:
                            words=[]
                            for word_ in word_lines[current_index:current_index+4]:
                                for wo in word_:
                                    words.append(wo['word'])
                            print(f'############### here words to consider for nextline',words)
                            for ident in other_identifers[base_identifier['word']]:
                                if not is_word_present(ident, words, threshold=0.95):
                                    print(f'############### identifier not found in this line and the ident is',ident)
                                    valid=False
                                    break

                        if not valid:
                            continue

                        elif end_point:
                            print(f'################ end_point',end_point,'for',word)
                            cordinates.append([word['pg_no'],word['top'],end_point['pg_no'],end_point['bottom']])
                                
                        elif not end_point:
                            print(f'################ no end_point',end_point,'for',word)
                            cordinates.append([word['pg_no'],word['top']])
                            
    print(f'################ cordinates',cordinates)
    for page in reversed(ocr_word_all):
        if page:  # non-empty list
            last_page_words = page
            break

    # Sort if there are words
    last_page = sorted(last_page_words, key=lambda x: x["top"]) if last_page_words else []

    print(f'################ last_page',last_page)
    if cordinates and len(cordinates[-1])<4:
        # print(f'############### we have didnt find any end point in the last so appending last wrd of last page',last_page[-1])
        cordinates[-1].extend([last_page[-1]['pg_no'],last_page[-1]['bottom']])

    # print(f'cordinates',cordinates)
    reamark_cordinates=[]
    for i in range(len(cordinates)):

        current=cordinates[i]
        if i == len(cordinates)-1:
            next_=[last_page[-1]['pg_no'],last_page[-1]['bottom']]
        else:
            next_=cordinates[i+1]
        merged = current[:2] + next_[:2] 
        reamark_cordinates.append(merged)

    remarks_section_ocr=[]
    for cordinate in reamark_cordinates:
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_word_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word=word_line[0]
                if word['top'] >= end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top'] >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    section[word['pg_no']].extend(word_line)
            if stop:
                break

        remarks_section_ocr.append(section)

    print(f'section ocr satrting here')
    all_sections=[]
    index=-1
    all_headers=[] 
    for cordinate in cordinates:
        index=index+1
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_word_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word_line=sorted(word_line, key=lambda x: (x["pg_no"], x["top"]))
                word=word_line[0]
                if word['bottom'] > end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top']+5 >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    # print(f"start word is {word}")
                    section[word['pg_no']].extend(word_line)
            if stop:
                break
        # print(f'one section ending here',section.keys())
        all_sections.append(section)


    print(f'section ocr 2 satrting here')
    all_headers=[]  
    all_ocr_sections=[]
    index=-1
    for cordinate in cordinates:
        index=index+1
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_data_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            if not page:
                continue
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word_line=sorted(word_line, key=lambda x: (x["pg_no"], x["top"]))
                word=word_line[0]
                if word['bottom'] > end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top']+5 >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    # print(f"start word is {word}")
                    section[word['pg_no']].extend(word_line)
            if stop:
                break

        all_ocr_sections.append(section)
                
    return all_sections,cordinates,all_ocr_sections,remarks_section_ocr


------------------------------------------------------------------------------------------------------------------------------
def line_wise_ocr_data(words):
    """
    Forms the values in each line and creates line-wise OCR data.

    Args:
        words: List of dictionaries containing OCR data.

    Returns:
        list: List of lists where each inner list represents words on the same horizontal line.
    """
    ocr_word = []

    # Sort words based on their 'top' coordinate
    sorted_words = sorted(filter(lambda x: isinstance(x, dict) and "pg_no" in x and "top" in x, words), key=lambda x: (x["pg_no"], x["top"]))

    # sorted_words = sorted(words, key=lambda x: (x["pg_no"], x["top"]))

    # Group words on the same horizontal line
    line_groups = []
    current_line = []

    for word in sorted_words:
        if not current_line:
            # First word of the line
            current_line.append(word)
        else:
            diff = abs(word["top"] - current_line[0]["top"])
            if diff < 5:
                # Word is on the same line as the previous word
                current_line.append(word)
            else:
                # Word is on a new line
                current_line=sorted(current_line, key=lambda x: x["left"])
                line_groups.append(current_line)
                current_line = [word]

    # Add the last line to the groups
    if current_line:
        current_line=sorted(current_line, key=lambda x: x["left"])
        line_groups.append(current_line)
        
    for line in line_groups:
        line_words = [word["word"] for word in line]
        # print(" ".join(line_words))

    return line_groups


-------------------------------------------------------------------------------------------------------------
def find_extra_headers(second_headers,ocr_data):

    found_extra_headers={}

    for extra_head in second_headers:

        print(f'finding extra header is {extra_head}')

        ocr=extra_head['croppedOcrAreas']
        mapped_head=extra_head['value']

        words=[word['word'] for word in ocr if re.sub(r'[^a-zA-Z%#]', '', word['word'])]
        print(f'header words aree {words}')

        possible_header=find_accurate_table_header(ocr_data,words)

        if possible_header:
            found_extra_headers[mapped_head]=possible_header

    print(f'final extra header groups are {found_extra_headers}')

    
    second_header_box= combine_dicts(list(found_extra_headers.values()))

    return found_extra_headers,second_header_box


---------------------------------------------------------------------------------------------------------------------------------------
def predict_paragraph(para_fields,ocr_word_all):

    para_field,para_high={},{}

    for field,section_identifier in para_fields.items():

        print(f" ################# identifiers['section_identifiers']",section_identifier)
        if not section_identifier:
            return None,None,None,None
        
        start=section_identifier[0]
        print(f" ################# start",start)

        start_idenitfier={}
        if start:
            start_idenitfier=combine_dicts(start)
            print(f" ################# start_identifiers",start_idenitfier)

        if not start:
            continue

        try:
            end=section_identifier[1]
        except:
            end=[]
        print(f" ################# end",end)
        end_identifiers={}
        if end:
            end_identifiers=combine_dicts(end)
            print(f" ################# end_identifiers",end_identifiers)

        start_matcher=False
        end_matcher=False
        stop=False
        needed_lines=[]
        for page in ocr_word_all:
            sorted_words = sorted(page, key=lambda x: (x["top"]))
            word_lines=line_wise_ocr_data(sorted_words)
            current_index=-1
            for line in word_lines:
                current_index=current_index+1
                for word in line:
                    cleaned_word=re.sub(r'[^a-zA-Z]', '', word['word'])
                    base_identifier_word=re.sub(r'[^a-zA-Z]', '', start_idenitfier['word'])
                    if base_identifier_word and not start_matcher:
                        start_matcher = is_fuzzy_subsequence(base_identifier_word, cleaned_word)
                        if start_matcher:
                            print(f" ################# start_matcher found at",word['word'])
                            break
                    
                    base_end_identifier_word=re.sub(r'[^a-zA-Z]', '', end_identifiers['word'])
                    if base_end_identifier_word:
                        end_matcher = is_fuzzy_subsequence(base_end_identifier_word,cleaned_word)
                        if end_matcher:
                            print(f" ################# end_matcher found at",word['word'])
                            break

                if start_matcher and not end_matcher:
                    needed_lines.extend(line)
                elif start_matcher and end_matcher:
                    needed_lines.extend(line)
                    stop=True

                if stop:
                    break
            
            if stop:
                break
            
        print(f" ################# found needed_lines are",needed_lines)

        if needed_lines:
            needed_para=''
            needed_para_high=[]
            needed_lines=line_wise_ocr_data(needed_lines)
            for line in needed_lines:
                sorted_para_line = sorted(line, key=lambda x: (x["right"]))
                for wor in sorted_para_line:
                    needed_para=needed_para+' '+wor['word']
                needed_para_high.extend(line)
            print(f" ################# found needed_para is",needed_para)
            para_field[field]=needed_para
            para_high[field]=from_highlights(combine_dicts(needed_para_high))

    return para_field,para_high

def ionic_extraction():

    data = request.json
    print(f"Data recieved: {data}")
    try:
        tenant_id = data['tenant_id']
        case_id = data.get('case_id', None)
        process = data.get('tenant_id', None)
    except Exception as e:
        print(f'## TE Received unknown data. [{data}] [{e}]')
        return {'flag': False, 'message': 'Incorrect Data in request'}

    db_config['tenant_id'] = tenant_id
    extraction_db = DB('extraction', **db_config)
    queue_db = DB('queues', **db_config)    

    container_name = data.get('container', None)

    try:

        query = f"SELECT `document_id`  from  `process_queue` where `case_id` = '{case_id}';"
        document_ids=queue_db.execute_(query)["document_id"].to_list()
        # print(f"The result is {document_ids}")
        
        for document_id in document_ids:

            query = f"SELECT format_type,template_name,format_pages from  `ocr` where `case_id` = '{case_id}' and document_id ='{document_id}'"
            ocr_data=extraction_db.execute_(query)
            # print(f"The result is {ocr_data}")
            
            queue_db = DB('queues', **db_config)
            template_db = DB('template_db', **db_config)

            query = f"SELECT `ocr_word`,ocr_data from  `ocr_info` where `case_id` = '{case_id}'and document_id ='{document_id}'"
            ocr_data_all = queue_db.execute_(query)['ocr_word'].to_list()[0]
            ocr_data_all=json.loads(ocr_data_all)
            ocr_all = queue_db.execute_(query)['ocr_data'].to_list()[0]
            ocr_all=json.loads(ocr_all)

            format_types=ocr_data.to_dict(orient='records')

            for format_data in format_types:

                act_format_data=format_data['format_type']
                # print(f"format extarction is going start for {act_format_data}")

                format_page=format_data['format_type']
                identifier=format_data['template_name']

                extracted_table={}
                extracted_fields={}
                fields_highlights={}

                if not format_page or not identifier:
                    continue

                # print(F"foramt got is {format_page.rsplit('_', 1)}")
                format= format_page.rsplit('_', 1)[0]
                pages=format_page.rsplit('_', 1)[1]
                start=int(pages.split('@')[0])
                end=int(pages.split('@')[1])
                # print(f'start is {start} and end is {end}')
                ocr_pages=[]
                for pag in ocr_data_all:
                    if not pag:
                        continue
                    page_no=int(pag[0]['pg_no'])-1
                    if start<=page_no<=end:
                        print(start,page_no,end)
                        ocr_pages.append(pag)
                
                ocr_data_pages=[]
                for pag in ocr_all:
                    if not pag:
                        continue
                    page_no=int(pag[0]['pg_no'])-1
                    if start<=page_no<=end:
                        ocr_data_pages.append(pag)

                query = f"SELECT * from  `trained_info` where format='{format}' and identifier='{identifier}'"
                process_trained_fields = template_db.execute_(query).to_dict(orient='records')

                if process_trained_fields:
                    process_trained_fields=process_trained_fields[0]
                    # print(f"ocr_pages sending are {ocr_pages}")
                    start_pages=predict_mutli_checks(ocr_pages,ocr_data_pages,process_trained_fields,end)

                    if len(start_pages)>1:

                        del_rec=f'delete from ocr where case_id ="{case_id}" and format_type ="{format_page}"'
                        extraction_db.execute_(del_rec)

                        for pair in start_pages:
                            if len(pair)==1:
                                end_page=end
                            else:
                                end_page=pair[1]
                            start_page=pair[0]

                            formated=format+'_'+str(start_page)+'@'+str(end_page)
                            ne_pages=extract_page_list(formated)
                            query = "insert into `ocr` (template_name,case_id,format_type,document_id,format_pages) values (%s,%s,%s,%s,%s)"
                            params = [identifier,case_id, formated,case_id,json.dumps(ne_pages)]
                            extraction_db.execute_(query,params=params)

            query = f"SELECT format_type,template_name,format_pages from  `ocr` where `case_id` = '{case_id}' and document_id ='{document_id}'"
            case_data=extraction_db.execute_(query)

            format_types=case_data.to_dict(orient='records')
            
            for format_data in format_types:

                act_format_data=format_data['format_type']
                # print(f"format extarction is going start for {act_format_data}")

                format_page=format_data['format_type']
                identifier=format_data['template_name']

                extracted_table={}
                extracted_fields={}
                fields_highlights={}

                if not format_page:
                    continue

                # print(F"foramt got is {format_page.rsplit('_', 1)}")
                format= format_page.rsplit('_', 1)[0]
                pages=format_page.rsplit('_', 1)[1]
                start=int(pages.split('@')[0])
                end=int(pages.split('@')[1])
                # print(f'start is {start} and end is {end}')
                ocr_pages=[]
                for pag in ocr_data_all:
                    if not pag:
                        continue
                    page_no=int(pag[0]['pg_no'])-1
                    if start<=page_no<=end:
                        print(start,page_no,end)
                        ocr_pages.append(pag)
                
                ocr_data_pages=[]
                for pag in ocr_all:
                    if not pag:
                        continue
                    page_no=int(pag[0]['pg_no'])-1
                    if start<=page_no<=end:
                        ocr_data_pages.append(pag)

                if not ocr_pages or not ocr_data_pages:
                    continue

                print(f'len of ocr pages {len(ocr_pages)}')
                print(f'len of ocr pages {len(ocr_data_pages)}')

                # print(F" ########## exarction starting for foramt {format} and start and end pages got are {start} {end}")

                query = f"SELECT * from  `process_training_data` where format='{format}' and model_usage = 'yes'"
                master_process_trained_fields = template_db.execute_(query)

                if not master_process_trained_fields.empty:
                    master_process_trained_fields=master_process_trained_fields.to_dict(orient='records')[0]
                else:
                    master_process_trained_fields={}
                
                query = f"SELECT * from  `trained_info` where format='{format}' and identifier='{identifier}'"
                process_trained_fields = template_db.execute_(query)
                
                used_version=''
                if process_trained_fields.empty:
                    extarction_from={}

                    print(f'skkiping the eod {format_page}')
                    if start==end and format == 'eob':
                        print(f'skkiping the eod {format_page}')
                        continue

                    if not master_process_trained_fields:
                        continue

                    process_trained_fields=master_process_trained_fields
                    trained=process_trained_fields['trained']
                    process_trained_fields['values']=process_trained_fields['values_trained']
                    common_fields=process_trained_fields['fields_common']
                    
                    if trained:
                        print(F" ################# creating models real_time")
                        create_models_real_time(process,format,process_trained_fields,case_id)

                        extracted_fields,fields_highlights,extracted_headers=get_master_extraction_values(process,format,case_id,ocr_pages,json.loads(master_process_trained_fields['fields']),common_fields)
                        used_version='1'

                        query=f'update ocr set extracted_headers = %s where case_id = %s and format_type = %s'
                        extraction_db.execute_(query,params=[json.dumps(extracted_headers),case_id,format_page])

                    else:
                        if process_trained_fields['fields']:
                            fields=json.loads(process_trained_fields['fields'])
                            print(F" we dont ave any master template so fields are not extarcted so {fields}")
                            for field in fields:
                                extracted_fields[field]=''
                                
                else:
                    process_trained_fields=process_trained_fields.to_dict(orient='records')
                    extracted_table={}
                    extracted_fields={}
                    extarction_from={}
                    extracted_remarks={}
                    remarks_high={}

                    if process_trained_fields:
                        process_trained_fields= process_trained_fields[0]
                        #here we will extract any over all thing
                        fields_data = process_trained_fields['fields'] if process_trained_fields['fields'] else ''
                        if fields_data:
                            print(f'fields_data is {fields_data}')
                            extracted_fields['main_fields'], fields_highlights['main_fields'] = get_template_extraction_values(ocr_pages, ocr_data_pages, process_trained_fields, json.loads(fields_data))
                            # extracted_fields['main_fields'],fields_highlights['main_fields']=get_template_extraction_values(ocr_pages,ocr_data_pages,process_trained_fields,json.loads(process_trained_fields['fields']))
                            extarction_from['main_fields']=list(extracted_fields['main_fields'].keys())
                            print(F" #################### here table to extract is {fields_highlights['main_fields']}")
                        
                        if process_trained_fields['trained_table']:
                            process_trained_fields['trained_table']=json.loads(process_trained_fields['trained_table'])
                            for table_name,tables in process_trained_fields['trained_table'].items():
                                if len(tables)>2:
                                    table_header=tables[0]
                                    table_header_text=[]
                                    if 'table' in tables:
                                        table_header_text=tables[2]['table']['headers']
                                    elif 'headers' in tables[2]:
                                        table_header_text=tables[2]['headers']

                                    if table_header:
                                        found_header,table_headers_line=extract_table_header(ocr_data_pages,0,table_header,table_header_text=table_header_text)

                                    table_footer=tables[1]
                                    if table_footer:
                                        found_footer,table_foot_line=extract_table_header(ocr_data_pages,0,table_footer,True)

                                    if found_header:
                                        if found_footer:
                                            bottom=found_footer[0]['top']
                                        else:
                                            bottom=1000
                                        extracted_table,table_high=extract_table_from_header(extraction_db,template_db,case_id,ocr_data_pages,found_header,table_headers_line,0,bottom)
                                        # print(F" extracted_table #################### {extracted_table}")

                                        # if 'table' in table_high:
                                        #     fields_highlights['main_fields']['table']=table_high['table']
                                        #     extracted_fields['main_fields']['table']=extracted_table

                        remarks=process_trained_fields.get('remarks',{})
                        print(f' remarks need to be extracted are {remarks}')
                        if remarks:
                            print(f'remarks here are {remarks}')
                            remarks=json.loads(remarks)
                            if remarks and remarks.get('type','None') == 'check level':
                                extracted_remarks,remarks_high=extract_remarks(remarks.get('start',[]),remarks.get('end',[]),ocr_pages)

                        #here we will extract any sessions things
                        # print(F" here extract for section {process_trained_fields['sub_template_identifiers']}")
                        if process_trained_fields['sub_template_identifiers']:

                            sub_template_identifiers=json.loads(process_trained_fields['sub_template_identifiers'])
                            all_section_fields=json.loads(process_trained_fields['section_fields'])
                            table=json.loads(process_trained_fields['section_table'])

                            try:
                                table_t2=json.loads(process_trained_fields['section_table_t2'])
                            except:
                                table_t2={}

                            if table_t2:
                                print(f'this table has a t2 trained table')
                                table=table_t2

                            print(F" all_section_fields {all_section_fields}")

                            for section,identifiers in sub_template_identifiers.items():

                                if not all_section_fields:
                                    continue

                                section_fields=all_section_fields[section]

                                extarction_from[section]=[]
                                # print(F" section #################### {section}")
                                extracted_fields[section]=[]
                                fields_highlights[section]=[]
                                section_header=[]
                                if 'section_exceptions' in  identifiers:
                                    section_header=identifiers['section_exceptions']

                                if 'sub_section' in  identifiers and identifiers['sub_section']:
                                    sub_section=identifiers['sub_section']
                                    sub_section_identifiers=sub_section['identifiers']
                                    sub_section_fields=sub_section['selected_fields']

                                paraFieldsTraining={}
                                if 'paraFieldsTraining' in  identifiers and identifiers['paraFieldsTraining']:
                                    paraFieldsTraining=identifiers['paraFieldsTraining']

                                # print(F"################N section_header is {section_header}")
                                sub_templates,cordinates,all_ocr_sections,remarks_section_ocr=predict_sub_templates(identifiers['section_identifiers'],ocr_pages,ocr_data_pages,section_header,process_trained_fields)
                                print(F" main section cordinates {cordinates}")
                                if not sub_templates:
                                    continue

                                section_no=-1
                                # print(F" #################### sub_templates {len(sub_templates)}")
                                claim_ids=[]
                                for template_ocr in sub_templates:
                                    
                                    if 'sub_section' in  identifiers and identifiers['sub_section']:

                                        section_no=section_no+1

                                        sub_section=identifiers['sub_section']
                                        sub_section_identifiers=sub_section['identifiers']
                                        common_section_fields=sub_section['selected_fields']

                                        common_template_fields={}
                                        common_template_highlights={}
                                        if common_section_fields:
                                            common_template_fields['fields'],common_template_highlights['fields']=get_template_extraction_values(list(template_ocr.values()),list(all_ocr_sections[section_no].values()),process_trained_fields,section_fields,common_section=True,common_section_fields=common_section_fields)
                                        print(f'common_fields is {common_template_fields}')

                                        sub_sub_templates,sub_cordinates,sub_all_ocr_sections,sub_remarks_section_ocr=predict_sub_sub_templates(sub_section_identifiers,list(template_ocr.values()),list(all_ocr_sections[section_no].values()))
                                        print(F" sub section cordinates {sub_cordinates}")
                                        #loop for sub sub section starts here 

                                        sub_section_no=-1
                                        for sub_template_ocr in sub_sub_templates:

                                            sub_section_no=sub_section_no+1
                                            template_fields={}
                                            template_highlights={}
                                            if not sub_template_ocr:
                                                continue

                                            print(F" #################### sub_section_no is {sub_section_no}")
                                            print(F" #################### ocr_data is {list(sub_template_ocr.values())}")

                                            template_fields['fields'],template_highlights['fields']=get_template_extraction_values(list(sub_template_ocr.values()),list(sub_all_ocr_sections[sub_section_no].values()),process_trained_fields,section_fields,sub_section=True,common_section_fields=common_section_fields)

                                            if common_template_fields:
                                                template_fields['fields'].update(common_template_fields['fields'])
                                                template_highlights['fields'].update(common_template_highlights['fields'])

                                            print(f"template_fields is {template_fields['fields']}")

                                            extarction_from[section].append(list(template_fields['fields'].keys()))
                                            # print(F" #################### template_fields {template_fields}")
                                            # print(F" #################### cordinates {cordinates} and section_no {section_no}")

                                            if section in table and table[section]:
                                                print(F"section is {section}")
                                                # print(F" #################### cordinates {cordinates} and section_no {section_no}")
                                                page_no=sub_cordinates[sub_section_no][0]
                                                section_top=sub_cordinates[sub_section_no][1]
                                                trained_tables=table[section]
                                                print(F"trained_tables is {trained_tables}")
                                                template_fields['table']={}
                                                template_highlights['table']={}

                                                # print(" ################ all_ocr_sections start line is",all_ocr_sections[section_no])
                                                table_extract=False
                                                max_match=0
                                                needed_table=''
                                                for table_name,tables in trained_tables.items():

                                                    print(F"table_name is  here is to idnetify the table {table_name}")

                                                    if table_name == 'table':
                                                        continue
                                                    if tables and len(tables)>2:
                                                        print(F"tables is {tables[0]}")
                                                        table_header=tables[0]
                                                        table_header_text=tables[2]
                                                        if 'table' in table_header_text:
                                                            table_header_text=table_header_text['table'].get('headers',[])
                                                        else:
                                                            table_header_text=table_header_text.get('headers',[])
                                                        header_lines=[]
                                                        if table_header:
                                                            header_lines=extract_table_header(list(sub_all_ocr_sections[sub_section_no].values()),section_top,table_header,table_header_text=table_header_text,header_check=True)
                                                            print(F"found_header is {header_lines}")
                                                            if not header_lines:
                                                                for ocr in ocr_all:
                                                                    if not pag:
                                                                        continue
                                                                    header_lines=extract_table_header([ocr],0,table_header,table_header_text=table_header_text,header_check=True)
                                                                    print(F"found_header is {header_lines}")
                                                                    if header_lines:
                                                                        break
                                                        if header_lines:
                                                            table_headers_line=line_wise_ocr_data(table_header)
                                                            table_line_words=''
                                                            for table_head_line in table_headers_line:
                                                                for word in table_head_line:
                                                                    table_line_words=table_line_words+" "+word['word']
                                                            print(F"table_line_words is {table_line_words}")

                                                            header_lines_found=line_wise_ocr_data(header_lines)
                                                            headee_line_words=''
                                                            for header_line_found in header_lines_found:
                                                                for word in header_line_found:
                                                                    headee_line_words=headee_line_words+" "+word['word']
                                                            print(F"headee_line_words is {headee_line_words}")
                                                        
                                                            matcher = SequenceMatcher(None, table_line_words, headee_line_words)
                                                            similarity_ratio_col = matcher.ratio()
                                                            print(F"similarity_ratio_col is {similarity_ratio_col} for the tabke is {table_name}")

                                                            if similarity_ratio_col>max_match:
                                                                max_match=similarity_ratio_col
                                                                needed_table=table_name

                                                for table_name,tables in trained_tables.items():

                                                    if table_name == 'table':
                                                        continue

                                                    if needed_table and needed_table !=table_name:
                                                        continue


                                                    trained_map={}
                                                    needed_headers=[]
                                                    if tables and len(tables)>3:
                                                        trained_map_got=tables[3]
                                                        # print(F"trained_map is {trained_map_got}")
                                                        trained_map={}
                                                        for key,value in trained_map_got.items():
                                                            if key.startswith("New Column") and value.startswith("New Column"):
                                                                continue
                                                            if key.startswith("New Column"):
                                                                trained_map[value] = value
                                                            else:
                                                                trained_map[key] = value
                                                        # print(F"trained_map is {trained_map}")

                                                    extra_variables=[]
                                                    if tables and len(tables)>4:
                                                        extra_variables=tables[4]
                                                    print(F"extra_variables is {extra_variables}")

                                                    no_header_columns=[]
                                                    if tables and len(tables)>5:
                                                        no_header_columns=tables[5]
                                                    print(F"no_header_columns is {no_header_columns}")
                                                        
                                                    if tables and len(tables)>2:
                                                        print(F"tables is {tables[0]}")
                                                        table_header=tables[0]
                                                        table_header_text=tables[2]
                                                        if 'table' in table_header_text:
                                                            table_header_text=table_header_text['table'].get('headers',[])
                                                        else:
                                                            table_header_text=table_header_text.get('headers',[])

                                                        if trained_map:
                                                            trained_map = dict(
                                                                sorted(
                                                                    trained_map.items(),
                                                                    key=lambda x: (table_header_text.index(x[0]) if x[0] in table_header_text else
                                                                                table_header_text.index(x[1]) if x[1] in table_header_text else float('inf'))
                                                                )
                                                            )
                                                            table_header_text=trained_map.values()
                                                            needed_headers=trained_map.keys()

                                                        if table_header:
                                                            head_page=[]
                                                            found_header,table_headers_line=extract_table_header(list(sub_all_ocr_sections[sub_section_no].values()),section_top,table_header,table_header_text=table_header_text)
                                                            print(F"found_header is {found_header}")
                                                            if not found_header:
                                                                for ocr in ocr_all:
                                                                    if not pag:
                                                                        continue
                                                                    found_header,table_headers_line=extract_table_header([ocr],0,table_header,table_header_text=table_header_text)
                                                                    print(F"found_header is {found_header}")
                                                                    if found_header:
                                                                        break
                                                        

                                                        table_footer=tables[1]
                                                        found_footer=None
                                                        if table_footer:
                                                            found_footer,table_foot_line=extract_table_header(list(sub_all_ocr_sections[sub_section_no].values()),section_top,table_footer,True)
                                                        
                                                        if found_header:
                                                            if found_footer:
                                                                bottom=found_footer[0]['top']
                                                                bottom_page=found_footer[0]['pg_no']
                                                            else:
                                                                bottom=1000
                                                                bottom_page=False
                                                            print(F"found_header is {found_header}")
                                                            print(F"found_footer is {found_footer}")

                                                            template_extracted_table,table_high=extract_table_from_header(extraction_db,template_db,case_id,list(sub_all_ocr_sections[sub_section_no].values()),found_header,table_headers_line,section_top,bottom=bottom,cord=sub_cordinates[sub_section_no],trained_map=trained_map,bottom_page=bottom_page,extra_variables=extra_variables,no_header_columns=no_header_columns)
                                                            print(F" template_extracted_table #################### {template_extracted_table}")

                                                            # if needed_headers:
                                                            #     template_extracted_table=filter_columns(template_extracted_table, needed_headers)

                                                            if 'table' in table_high:
                                                                template_highlights['table'][table_name]=table_high['table']

                                                            template_fields['table'][table_name]=template_extracted_table
                                                        else:
                                                            template_fields['table'][table_name]={}

                                                        if template_fields['table'][table_name]:
                                                            table_extract=True
                                                            break

                                                if not table_extract:
                                                    template_fields['table']={}
                                                    template_fields['table']['table_1']={}

                                                print(f' remarks need to be extracted are {remarks}')
                                                if remarks and remarks.get('type','None') == 'claim level':
                                                    extracted_remarks,remarks_high=extract_remarks(remarks.get('start',[]),remarks.get('end',[]),list(remarks_section_ocr[section_no].values()))

                                                if extracted_remarks:
                                                    template_fields['remarks']=extracted_remarks
                                                    template_highlights['remarks']=remarks_high

                                            fields_highlights[section].append(template_highlights)
                                            extracted_fields[section].append(template_fields)

                                    else:
                                        template_fields={}
                                        template_highlights={}

                                        if not template_ocr:
                                            continue

                                        section_no=section_no+1
                                        print(F" #################### section_no is {section_no}")
                                        print(F" #################### ocr_data is {list(template_ocr.values())}")

                                        section_fields=all_section_fields[section]
                                        template_fields['fields'],template_highlights['fields']=get_template_extraction_values(list(template_ocr.values()),list(all_ocr_sections[section_no].values()),process_trained_fields,section_fields,section_fields=True)
                                        extarction_from[section].append(list(template_fields['fields'].keys()))
                                        # print(F" #################### template_fields {template_fields}")
                                        # print(F" #################### cordinates {cordinates} and section_no {section_no}")

                                        if section in table and table[section]:

                                            # print(F" #################### cordinates {cordinates} and section_no {section_no}")
                                            page_no=cordinates[section_no][0]
                                            section_top=cordinates[section_no][1]
                                            trained_tables=table[section]
                                            template_fields['table']={}
                                            template_highlights['table']={}

                                            # print(" ################ all_ocr_sections start line is",all_ocr_sections[section_no])
                                            table_extract=False
                                            max_match=0
                                            needed_table=''
                                            print(F"trained_tables is {trained_tables}")
                                            for table_name,tables in trained_tables.items():
                                                if table_name == 'table':
                                                    continue
                                                if tables and len(tables)>2:
                                                    print(F"tables is {tables[0]}")
                                                    table_header=tables[0]
                                                    table_header_text=tables[2]
                                                    if 'table' in table_header_text:
                                                        table_header_text=table_header_text['table'].get('headers',[])
                                                    else:
                                                        table_header_text=table_header_text.get('headers',[])
                                                    header_lines=[]
                                                    if table_header:
                                                        header_lines=extract_table_header(list(all_ocr_sections[section_no].values()),section_top,table_header,table_header_text=table_header_text,header_check=True)
                                                        print(F"found_header is {header_lines}")
                                                        if not header_lines:
                                                            for ocr in ocr_all:
                                                                if not pag:
                                                                    continue
                                                                header_lines=extract_table_header([ocr],0,table_header,table_header_text=table_header_text,header_check=True)
                                                                print(F"found_header is {header_lines}")
                                                                if header_lines:
                                                                    break
                                                    if header_lines:
                                                        table_headers_line=line_wise_ocr_data(table_header)
                                                        table_line_words=''
                                                        for table_head_line in table_headers_line:
                                                            for word in table_head_line:
                                                                table_line_words=table_line_words+" "+word['word']
                                                        print(F"table_line_words is {table_line_words}")

                                                        header_lines_found=line_wise_ocr_data(header_lines)
                                                        headee_line_words=''
                                                        for header_line_found in header_lines_found:
                                                            for word in header_line_found:
                                                                headee_line_words=headee_line_words+" "+word['word']
                                                        print(F"headee_line_words is {headee_line_words}")
                                                    
                                                        matcher = SequenceMatcher(None, table_line_words, headee_line_words)
                                                        similarity_ratio_col = matcher.ratio()
                                                        print(F"similarity_ratio_col is {similarity_ratio_col}")
                                                        if similarity_ratio_col>max_match:
                                                            needed_table=table_name


                                            for table_name,tables in trained_tables.items():

                                                if table_name == 'table':
                                                    continue

                                                print(f'needed table is {needed_table}')
                                                if needed_table and needed_table !=table_name:
                                                    continue


                                                trained_map={}
                                                needed_headers=[]
                                                if tables and len(tables)>3:
                                                    trained_map_got=tables[3]
                                                    # print(F"trained_map is {trained_map_got}")
                                                    trained_map={}
                                                    for key,value in trained_map_got.items():
                                                        if key.startswith("New Column"):
                                                            trained_map[value] = value
                                                        elif value.startswith("New Column"):
                                                            trained_map[key] = key
                                                        else:
                                                            trained_map[key] = value
                                                    # print(F"trained_map is {trained_map}")

                                                extra_variables=[]
                                                if tables and len(tables)>4:
                                                    extra_variables=tables[4]
                                                print(F"extra_variables is {extra_variables}")

                                                no_header_columns=[]
                                                if tables and len(tables)>5:
                                                    no_header_columns=tables[5]
                                                print(F"no_header_columns is {no_header_columns}")
                                                    
                                                if tables and len(tables)>2:
                                                    table_header=tables[0]
                                                    table_header_text=tables[2]
                                                    if 'table' in table_header_text:
                                                        table_header_text=table_header_text['table'].get('headers',[])
                                                    else:
                                                        table_header_text=table_header_text.get('headers',[])

                                                    if trained_map:
                                                        trained_map = dict(
                                                            sorted(
                                                                trained_map.items(),
                                                                key=lambda x: (table_header_text.index(x[0]) if x[0] in table_header_text else
                                                                            table_header_text.index(x[1]) if x[1] in table_header_text else float('inf'))
                                                            )
                                                        )
                                                        table_header_text=trained_map.values()
                                                        needed_headers=trained_map.keys()

                                                    found_header=[]
                                                    print(F"table_header is {table_header}")
                                                    if table_header:
                                                        head_page=[]
                                                        found_header,table_headers_line=extract_table_header(list(all_ocr_sections[section_no].values()),section_top,table_header,table_header_text=table_header_text)
                                                        print(F"found_header is here is{found_header}")

                                                        if found_header:
                                                            extra_headers=[]
                                                            found_extra_headers=[]
                                                            second_header_box=[]
                                                            if tables and len(tables)>6:
                                                                extra_headers=tables[6]
                                                            print(F"extra_headers is {extra_headers}")

                                                            header_page=found_header[0]['pg_no']
                                                            needed_ocr=[]
                                                            for page in list(all_ocr_sections[section_no].values()):
                                                                if page and page[0]['pg_no']==header_page:
                                                                    needed_ocr.append(page)

                                                            if extra_headers:
                                                                found_extra_headers,second_header_box=find_extra_headers(extra_headers,needed_ocr)

                                                        if not found_header:
                                                            for ocr in ocr_all:
                                                                if not pag:
                                                                    continue
                                                                found_header,table_headers_line=extract_table_header([ocr],0,table_header,table_header_text=table_header_text)
                                                                print(F"found_header is here is {found_header}")
                                                                if found_header:
                                                                    extra_headers=[]
                                                                    found_extra_headers=[]
                                                                    second_header_box=[]
                                                                    if tables and len(tables)>6:
                                                                        extra_headers=tables[6]
                                                                    print(F"extra_headers is here is {extra_headers}")

                                                                    found_extra_headers,second_header_box=find_extra_headers(extra_headers,[ocr])
                                                                    break
                                                    

                                                    table_footer=tables[1]
                                                    found_footer=None
                                                    print(F"table_footer is {table_footer}")
                                                    if table_footer:
                                                        found_footer,table_foot_line=extract_table_header(list(all_ocr_sections[section_no].values()),section_top,table_footer,True)
                                                    
                                                    if found_header:

                                                        if found_footer:
                                                            bottom=found_footer[0]['top']
                                                            bottom_page=found_footer[0]['pg_no']
                                                        else:
                                                            bottom=1000
                                                            bottom_page=False
                                                        print(F"found_header is {found_header}")
                                                        print(F"found_footer is {found_footer}")

                                                        template_extracted_table,table_high=extract_table_from_header(extraction_db,template_db,case_id,list(all_ocr_sections[section_no].values()),found_header,table_headers_line,section_top,bottom=bottom,cord=cordinates[section_no],trained_map=trained_map,bottom_page=bottom_page,extra_variables=extra_variables,no_header_columns=no_header_columns,found_extra_headers=found_extra_headers,second_header_box=second_header_box)
                                                        print(F" template_extracted_table #################### {template_extracted_table}")

                                                        # if needed_headers:
                                                        #     template_extracted_table=filter_columns(template_extracted_table, needed_headers)

                                                        if 'table' in table_high:
                                                            template_highlights['table'][table_name]=table_high['table']

                                                        template_fields['table'][table_name]=template_extracted_table
                                                    else:
                                                        template_fields['table'][table_name]={}

                                                    if template_fields['table'][table_name]:
                                                        table_extract=True
                                                        break


                                            if not table_extract:
                                                template_fields['table']={}
                                                template_fields['table']['table_1']={}


                                            print(f' remarks need to be extracted are {remarks}')
                                            if remarks and remarks.get('type','None') == 'claim level':
                                                extracted_remarks,remarks_high=extract_remarks(remarks.get('start',[]),remarks.get('end',[]),list(remarks_section_ocr[section_no].values()))

                                            if extracted_remarks:
                                                template_fields['remarks']=extracted_remarks
                                                template_highlights['remarks']=remarks_high


                                        if paraFieldsTraining:
                                            para_field,para_high=predict_paragraph(paraFieldsTraining,list(template_ocr.values()))
                                            print(para_field,'para_field')
                                            print(para_high,'para_high')
                                            for field,value in para_field.items():
                                                if field in template_fields['fields'] and value:
                                                    template_fields['fields'][field]=value
                                                    for field_high in template_highlights:
                                                        template_highlights['fields'][field_high]=para_high[field]

                                        fields_highlights[section].append(template_highlights)
                                        extracted_fields[section].append(template_fields)


                if extracted_fields:
                    update_into_db(tenant_id,extracted_fields,extracted_table,extraction_db,case_id,act_format_data,process,json.loads(master_process_trained_fields['fields']),used_version,document_id,extarction_from)
                    update_highlights(tenant_id,case_id,fields_highlights,act_format_data,document_id)
                
                # dir_path = os.path.join("/var/www/extraction_api/app/extraction_folder/", case_id)
                # try:
                #     # Delete the directory and its contents
                #     if os.path.exists(dir_path):
                #         shutil.rmtree(dir_path)
                #         print(f"Directory '{dir_path}' deleted successfully.")
                #     else:
                #         print(f"Directory '{dir_path}' does not exist.")
                        
                # except Exception as e:
                #     print(f"An error occurred while deleting the directory: {e}")

        #post Processing
        post_processing(extraction_db,queue_db,case_id)
    
        try:
            result_for_accuracy = checks_stored_field_acccuracy(tenant_id,case_id)
            print(f"#####result is {result_for_accuracy}")
        except Exception as e:
            print(f"##########Error is {e}")

        message="ionic_extraction api is sucessfull."

        container=load_controler(tenant_id,"business_rules")

        query = f"select no_of_process from load_balancer where container_name='{container}'"
        no_of_process = int(queue_db.execute_(query)['no_of_process'].to_list()[0])
        no_of_process=str(no_of_process+1)
        query=f"update load_balancer set no_of_process = '{no_of_process}' where container_name = '{container}'"
        queue_db.execute_(query)


        reponse = {"data":{"message":message,"container":container,'process_flag':'true'},"flag":True,"container":container,'process_flag':'true'}
    except Exception as e:
        queue_db.execute("update `process_queue` set  invalidfile_reason = %s where `case_id` = %s", params=[f"Error at Extraction Container",case_id])
    
        error_message = traceback.format_exc()
        print(f"########## Error is: {e}")
        print("########## Traceback details:")
        print(error_message)

        reponse = {"data":{"message":"Error at Extraction Container",'process_flag':'false'},"flag":True,'process_flag':'false'}

    query = f"select no_of_process from load_balancer where container_name='{container_name}'"
    no_of_process = int(queue_db.execute_(query)['no_of_process'].to_list()[0])
    no_of_process=str(no_of_process-1)
    query=f"update load_balancer set no_of_process = '{no_of_process}' where container_name = '{container_name}'"
    queue_db.execute_(query)

    return reponse
---------------------------------------------------------------------------------------------------------------------------------------------------------------------


def predict_mutli_checks(ocr_data_all_got,ocr_raw_pages,process_trained_fields,end):

    row_headers = process_trained_fields.get('row_headers', None)
    column_headers = process_trained_fields.get('column_headers', None)
    contexts = process_trained_fields.get('contexts', None)

    row_headers_t2 = process_trained_fields['row_headers_t2']
    column_headers_t2 = process_trained_fields['column_headers_t2']
    contexts_t2 = process_trained_fields['contexts_t2']

    # row_headers,column_headers,contexts=process_trained_fields['row_headers'],process_trained_fields['column_headers'],process_trained_fields['contexts']

    if column_headers:
        column_headers=json.loads(column_headers)
    else:
        column_headers={}
    if row_headers:
        row_headers=json.loads(row_headers)
    else:
        row_headers={}
    if contexts:
        contexts=json.loads(contexts)
    else:
        contexts={}

    if column_headers_t2:
        column_headers_t2=json.loads(column_headers_t2)
    else:
        column_headers={}
    if row_headers_t2:
        row_headers_t2=json.loads(row_headers_t2)
    else:
        row_headers_t2={}
    if contexts_t2:
        contexts_t2=json.loads(contexts_t2)
    else:
        contexts_t2={}
    
    
    extracted_fields={}

    fields=['Check Number','Check Amount']
    page_field_data={}

    for field in fields:

        print(F" #####################")
        print(F" #####################")
        print(F" #####################")
        print(F" ##################### fiels is {field}")
        print(F" #####################")
        print(F" #####################")
        print(F" #####################")

        extracted_fields[field]=''

        row_header_int=row_headers.get(field,[])
        context_int=contexts.get(field,[])

        row_header_int_t2=[]
        if row_headers_t2:
            row_header_int_t2=row_headers_t2.get(field,[])
        context_int_t2=[]
        if contexts_t2:
            context_int_t2=contexts_t2.get(field,[])

        print(f" ########### row_header_int_t2 got are  {row_header_int_t2}")
        print(f" ########### context_int_t2 got are  {context_int_t2}")


        if row_header_int_t2 and context_int_t2:
            row_header_int=row_header_int_t2
            context_int=context_int_t2

        print(f" ########### row_header_int got are  {row_header_int}")
        print(f" ########### context_int got are  {context_int}")

        context_box={}
        if 'context_box' in context_int:
            context_box=context_int['context_box']
        row_box={}
        if 'row_box' in row_header_int:
            row_box=row_header_int['row_box']
        value_box={}
        if 'value_box' in row_header_int:
            value_box=row_header_int['value_box']

        # print(F" ##################### len of ocr_data_all is {len(ocr_data_all)}")
        all_pairs_row_con=check_headers(row_header_int,context_int,copy.deepcopy(ocr_data_all_got),copy.deepcopy(ocr_raw_pages))

        for pair in all_pairs_row_con:

            row_header=pair[0]
            context=pair[2]

            print(f" ########### finalised_headers got are  {pair}")
            if not row_header:
                continue
        
            for ocr_word in ocr_data_all_got:
                if not ocr_word:
                    continue
                if ocr_word[0]['pg_no'] == row_header['pg_no']:
                    value_page_ocr_data=ocr_word
            
            if row_header:
                possible_values_row_got,multi_line=finding_possible_values(row_header,row_header_int,value_page_ocr_data)
                print(f" ################ possible_values_row got are {possible_values_row_got}")

            if value_box:
                possible_values_row=[]
                for value in possible_values_row_got:
                    if value_box['left']>=row_box['left'] and value['left']+10>=row_header['left']:
                        possible_values_row.append(value)
                    else:
                        possible_values_row.append(value)
            else:
                possible_values_row=possible_values_row_got
            print(f" ################ possible_values_row got are {possible_values_row}")

            max_calculated_diff=10000
        
            for value in possible_values_row:

                calculated_diff=0
                if row_header:
                    value_row_diff_cal=calculate_distance(row_header,value)
                    row_act_confidence=value_row_diff_cal
                    row_base_diff=row_header_int['value_thr']
                    row_conf=calculate_confidence(row_base_diff,row_act_confidence)
                
                    calculated_row_diff=abs(row_header_int['value_thr']-value_row_diff_cal)
                    calculated_diff=calculated_diff+calculated_row_diff

                if context:
                    
                    column_act_confidence=calculate_value_distance(context,value)
                    con_base_diff=context_int['value_thr']
                    con_conf=calculate_cont_confidence(con_base_diff,column_act_confidence)

                    value_con_diff_cal=calculate_value_distance(context,value)
                    calculated_con_diff=abs(context_int['value_thr']-value_con_diff_cal)
                    calculated_diff=calculated_diff+calculated_con_diff

            
                if max_calculated_diff>calculated_diff:
                    max_calculated_diff=calculated_diff
                    predicted=value

            print(f" ################ predicted value is {predicted['word']}")

            if predicted:
                pg = predicted['pg_no']
                page_field_data.setdefault(pg, {})[field] = predicted['word']

   # Now build ranges based on pages with required field count
    pages_with_checks = sorted([pg for pg, data in page_field_data.items()])
    print(f"pages_with_checks is {pages_with_checks}")
    print(f"page_field_data is {page_field_data}")

    ranges = []
    if pages_with_checks:
        # Filter out pages with no Check Number AND no Check Amount
        filtered_pages = []
        for pg in sorted(pages_with_checks):
            check_number = page_field_data.get(pg, {}).get("Check #", "")
            check_amount = page_field_data.get(pg, {}).get("Check Amount", "")
            if (check_number and re.sub(r'[^0-9]', '', check_number)) or (check_amount and re.sub(r'[^0-9]', '', check_amount)):
                filtered_pages.append(pg)

        if filtered_pages:
            # Decide whether to use Check Number or Check Amount
            use_check_number = any(
                page_field_data.get(pg, {}).get("Check #", "") and re.sub(r'[^0-9]', '', page_field_data.get(pg, {}).get("Check #", ""))
                for pg in filtered_pages
            )

            start_page = filtered_pages[0]
            prev_val = (
                re.sub(r'[^0-9]', '', page_field_data.get(start_page, {}).get("Check #", "")) 
                if use_check_number else 
                re.sub(r'[^0-9]', '', page_field_data.get(start_page, {}).get("Check Amount", ""))
            )

            for page in filtered_pages[1:]:
                curr_val = (
                    re.sub(r'[^0-9]', '', page_field_data.get(page, {}).get("Check #", "")) 
                    if use_check_number else 
                    re.sub(r'[^0-9]', '', page_field_data.get(page, {}).get("Check Amount", ""))
                )

                if curr_val != prev_val and curr_val:  # Change detected
                    ranges.append([start_page - 1, page - 2])
                    start_page = page
                    prev_val = curr_val

            # Add last range
            ranges.append([start_page - 1, end])

            print(f"Final ranges (filtered & based on {'Check #' if use_check_number else 'Check Amount'}): {ranges}")

    return ranges


-----------------------------------------------------------------------------------------------------------------------------------------------------------------



def create_models_real_time(process, format, process_trained_fields, case_id):
    column_header = json.loads(process_trained_fields['column_headers'])
    row_header = json.loads(process_trained_fields['row_headers'])
    context = json.loads(process_trained_fields['contexts'])
    values = json.loads(process_trained_fields['values'])
    others = json.loads(process_trained_fields['others'])

    dir_path = os.path.join("/var/www/extraction_api/app/extraction_folder/")
    os.makedirs(dir_path, exist_ok=True)
    print(f"Directory '{dir_path}' created successfully.")

    def process_part(part_data, others_input, file_prefix, is_value=False):
        try:
            json_file = f"{file_prefix}.json"
            model_file = f"{file_prefix}_logistic_regression_model.joblib"
            vectorizer_file = f"{file_prefix}_count_vectorizer.joblib"
            json_path = os.path.join(dir_path, json_file)
            model_path = os.path.join(dir_path, model_file)
            vectorizer_path = os.path.join(dir_path, vectorizer_file)

            if os.path.exists(json_path) and os.path.exists(model_path) and os.path.exists(vectorizer_path):
                print(f"Files for '{file_prefix}' already exist. Skipping...")
                return

            others_part = form_others(others, others_input)
            create_json_files(part_data, others_part, json_file, case_id, is_value)
            train_and_save_model(json_file, model_file, vectorizer_file, case_id)
            print(f"Creation of trained model for '{file_prefix}' is done")
        except Exception as e:
            print(f"Exception while processing '{file_prefix}' is: {e}")

    process_part(column_header, [row_header, context, values], f"{process}_{format}_column_headers")
    process_part(row_header, [column_header, context, values], f"{process}_{format}_row_headers")
    process_part(context, [row_header, column_header, values], f"{process}_{format}_context")
    process_part(values, [row_header, context, column_header], f"{process}_{format}_values", is_value=True)

    return True


------------------------------------------------------------------------------------------------------------------------------------------------

def get_template_extraction_values(ocr_data_all_got,ocr_raw_pages,process_trained_fields,fields,section_fields=False,common_section=False,sub_section=False,common_section_fields=[]):

    row_headers = process_trained_fields['row_headers']
    column_headers = process_trained_fields['column_headers']
    contexts = process_trained_fields['contexts']

    row_headers_t2 = process_trained_fields['row_headers_t2']
    column_headers_t2 = process_trained_fields['column_headers_t2']
    contexts_t2 = process_trained_fields['contexts_t2']

    # row_headers,column_headers,contexts=process_trained_fields['row_headers',{}],process_trained_fields['column_headers',{}],process_trained_fields['contexts',{}]

    if column_headers:
        column_headers=json.loads(column_headers)
    else:
        column_headers={}
    if row_headers:
        row_headers=json.loads(row_headers)
    else:
        row_headers={}
    if contexts:
        contexts=json.loads(contexts)
    else:
        contexts={}

    if column_headers_t2:
        column_headers_t2=json.loads(column_headers_t2)
    else:
        column_headers={}
    if row_headers_t2:
        row_headers_t2=json.loads(row_headers_t2)
    else:
        row_headers_t2={}
    if contexts_t2:
        contexts_t2=json.loads(contexts_t2)
    else:
        contexts_t2={}
    
    print(f" ########### all contexts_t2 got are  {contexts_t2}")
    print(f" ###########mall row_headers_t2 got are  {row_headers_t2}")
    print(f" ########### all column_headers_t2 got are  {column_headers_t2}")

    print(f" ########### all contexts got are  {contexts}")
    print(f" ########### all row_headers got are  {row_headers}")
    print(f" ###########all  column_headers got are  {column_headers}")
    
    extracted_fields={}
    fields_highlights={}

    for field in fields:

        if field in common_section_fields and sub_section:
            continue

        if field not in common_section_fields and common_section:
            continue 

        ocr_data_all=copy.deepcopy(ocr_data_all_got)
        print(F" #####################")
        print(F" #####################")
        print(F" #####################")
        print(F" ##################### fiels is {field}")
        print(F" #####################")
        print(F" #####################")
        print(F" #####################")

        extracted_fields[field]=''

        row_header_int=row_headers.get(field,[])
        column_header_int=column_headers.get(field,[])
        context_int=contexts.get(field,[])
        
        row_header_int_t2=[]
        if row_headers_t2:
            row_header_int_t2=row_headers_t2.get(field,[])
        column_header_int_t2=[]
        if column_headers_t2:
            column_header_int_t2=column_headers_t2.get(field,[])
        context_int_t2=[]
        if contexts_t2:
            context_int_t2=contexts_t2.get(field,[])

        print(f" ########### row_header_int_t2 got are  {row_header_int_t2}")
        print(f" ########### column_header_int_t2 got are  {column_header_int_t2}")
        print(f" ########### context_int_t2 got are  {context_int_t2}")


        if row_header_int_t2 and context_int_t2:
            row_header_int=row_header_int_t2
            column_header_int=column_header_int_t2
            context_int=context_int_t2
        
        print(f" ########### row_header_int got are  {row_header_int}")
        print(f" ########### column_header_int got are  {column_header_int}")
        print(f" ########### context_int got are  {context_int}")

        context_box={}
        if 'context_box' in context_int:
            context_box=context_int['context_box']
        row_box={}
        if 'row_box' in row_header_int:
            row_box=row_header_int['row_box']
        value_box={}
        if 'value_box' in row_header_int:
            value_box=row_header_int['value_box']

        # print(F" ##################### len of ocr_data_all is {len(ocr_data_all)}")
        finalised_headers=finalise_headers(row_header_int,column_header_int,context_int,copy.deepcopy(ocr_data_all_got),copy.deepcopy(ocr_raw_pages))

        column_header=finalised_headers['column_header']
        row_header=finalised_headers['row_header']
        context=finalised_headers['context']
        print(f" ########### finalised_headers got are  {finalised_headers}")
        if not row_header:
            continue
    
        for ocr_word in ocr_data_all_got:
            if not ocr_word:
                continue
            if ocr_word[0]['pg_no'] == row_header['pg_no']:
                value_page_ocr_data=ocr_word
        
        if row_header:
            possible_values_row_got,multi_line=finding_possible_values(row_header,row_header_int,value_page_ocr_data)
            print(f" ################ possible_values_row got are {possible_values_row_got}")

        print(f" ################ value_box got are {value_box}")
        print(f" ################ row_box got are {row_box}")
        print(f" ################ context_box got are {context_box}")
        if value_box:
            possible_values_row=[]
            for value in possible_values_row_got:
                if value_box['left']>=row_box['left'] and value['left']+10>=row_header['left']:
                    possible_values_row.append(value)
                else:
                    possible_values_row.append(value)
            
            trained_angle_rv=get_angle(value_box,row_box)
            trained_angle_cv=get_angle(value_box,context_box)

        else:
            possible_values_row=possible_values_row_got
        print(f" ################ possible_values_row got are {possible_values_row}")

        max_calculated_diff=10000
        predicted={}

        for value in possible_values_row:

            calculated_diff=0
            if row_header:
                value_row_diff_cal=calculate_distance(row_header,value)
                print(f'value is {value["word"]}')
                row_act_confidence=value_row_diff_cal
                row_base_diff=row_header_int['value_thr']
                row_conf=calculate_confidence(row_base_diff,row_act_confidence)
                print(f'row_act_confidence is {row_act_confidence}')
                print(f'row_base_diff is {row_base_diff}')
                print(f'row_conf is {row_conf}')
                # print(f"################ calculated_col_diff is  {row_header_int['value_thr']} for {value_row_diff_cal}")
                calculated_row_diff=abs(row_header_int['value_thr']-value_row_diff_cal)
                calculated_diff=calculated_diff+calculated_row_diff
                # print(f"################ calculated_diff is  {calculated_row_diff} for {value}")

            if context:
                
                column_act_confidence=calculate_value_distance(context,value)
                con_base_diff=context_int['value_thr']
                con_conf=calculate_cont_confidence(con_base_diff,column_act_confidence)
            
                print(f'value is {value["word"]}')
                print(f'column_confidence is {column_act_confidence}')
                print(f'con_base_diff is {con_base_diff}')
                print(f'con_conf is {con_conf}')

                value_con_diff_cal=calculate_value_distance(context,value)
                calculated_con_diff=abs(context_int['value_thr']-value_con_diff_cal)
                calculated_diff=calculated_diff+calculated_con_diff
                # print(f"################ calculated_diff is  {calculated_con_diff} for {value}")

            # print(f"################ calculated_diff is  {calculated_diff} for {value}")
            if max_calculated_diff>calculated_diff:

                angle_cv=get_angle(value,context)
                if value_box:
                    confidence = 1 - (min(abs(trained_angle_cv - angle_cv), 360 - abs(trained_angle_cv - angle_cv)) / 180)
                    confidence_percent_cv = round(confidence * 100, 2)
                    print(f"here angle_cv {angle_cv} and cal diff is {trained_angle_cv}")
                    print(f"here confidence_percent is {confidence_percent_cv}")

                angle_rv=get_angle(value,row_header)
                if value_box:
                    confidence = 1 - (min(abs(trained_angle_rv - angle_rv), 360 - abs(trained_angle_rv - angle_rv)) / 180)
                    confidence_percent_rv = round(confidence * 100, 2)
                    print(f"here angle_cv {angle_rv} and cal diff is {trained_angle_rv}")
                    print(f"here confidence_percent is {confidence_percent_rv}")
                # print(f"################ final predict is  {predicted}")
                # print(f"################ multi_line is  {multi_line}")
                try:
                    if value_box:
                        confindance= min([row_conf,con_conf,confidence_percent_rv,confidence_percent_cv])
                    else:
                        confindance= min([row_conf,con_conf])
                except Exception as e:
                    print("exception occured:::::{e}")

                print(f"here base_diff {calculated_diff} and cal diff is {row_conf,con_conf}a and {confindance}")
                max_calculated_diff=calculated_diff
                predicted=value

        if multi_line:
            predicted=find_y_values(predicted,value_page_ocr_data,True)

        print(f"################ final predict is  {predicted}")
        print('#################')
        print('\n')
        if predicted:
            extracted_fields[field]=predicted['word']
            fields_highlights[field]=from_highlights(predicted)     

    return extracted_fields,fields_highlights

-----------------------------------------------------------------------------------------------------------------------------------------------------------

def extract_table_header(ocr_data,top, table_headers, foot=False,table_header_text=[],header_check=False):
    """
    Extracts table data from OCR words starting from a predicted header. The function looks for the header
    and then traverses down, collecting rows of table data until it encounters an empty line, a large gap,
    or other stopping conditions.

    Args:
        words_ (list): List of dictionaries containing OCR data for words.
        div (str): Division identifier.
        seg (str): Segment identifier.

    Returns:
        list: Extracted table rows.
    """
    
    table_headers_line=line_wise_ocr_data(table_headers)
    table_line_words=[]
    for table_head_line in table_headers_line:
        temp=''
        for word in table_head_line:
            temp=temp+" "+word['word']
        table_line_words.append(temp)

    table_lines=[]
    print(F'table_headers is {table_line_words}')
    # Sort words by their "top" position to process lines vertically
    found=[]
    for table_line_word in table_line_words:
        temp_line=[]
        max_match=0
        for ocr in ocr_data:
            sorted_words = sorted(ocr, key=lambda x: x["top"])
            line_ocr=line_wise_ocr_data(sorted_words)
            for line in line_ocr:
                if line[0]['top']<top:
                    continue
                if foot:
                    line_words = [word["word"] for word in line]
                    line_words=" ".join(line_words)
                    line_words_temp=re.sub(r'[^a-zA-Z]', '', line_words)
                    table_line_word_temp=re.sub(r'[^a-zA-Z]', '', table_line_word)
                    matcher = SequenceMatcher(None, line_words_temp, table_line_word_temp)
                    similarity_ratio_col = matcher.ratio()
                    if similarity_ratio_col>max_match and similarity_ratio_col>0.65:
                        max_match=similarity_ratio_col
                        temp_line=line
                        print(f"table_lineis {line_words} and table header is {table_line_word} and {similarity_ratio_col}")
                else:
                    line_words = [word["word"] for word in line]
                    line_words=" ".join(line_words)
                    matcher = SequenceMatcher(None, line_words, table_line_word)
                    similarity_ratio_col = matcher.ratio()
                    if similarity_ratio_col>max_match and similarity_ratio_col>0.65:
                        max_match=similarity_ratio_col
                        temp_line=line
                        print(f"table_lineis {line_words} and table header is {table_line_word} and {similarity_ratio_col}")
            print(f"temp_line got for this page is {temp_line}")
            if temp_line:
                table_lines.extend(temp_line)
        if temp_line:
            found.append(table_line_word)  

    print(F'table_line is {table_lines}')
    if not table_lines or len(found)!=len(table_line_words):
        table_lines_=detect_table_header_2(table_headers,ocr_data)
        if not table_lines and not table_lines_:
            print("No table header detected.")
            if header_check:
                return []
            return [],[]
        elif table_lines_:
            table_lines=table_lines_

    table_header_box=combine_dicts(table_lines)

    if not table_header_box:
        return [],[] 

    final_line=[]
    for ocr in ocr_data:
        sorted_words = sorted(ocr, key=lambda x: x["top"])
        line_ocr=line_wise_ocr_data(sorted_words)
        for line in line_ocr:
            line_box=combine_dicts(line)
            if line_box and table_header_box['top']<=line_box['top']<=table_header_box['bottom'] and line_box['pg_no'] == table_header_box['pg_no']:
                print(F'final table lines are is {line_box}')
                final_line.extend(line)

    if header_check:
        return final_line
    
    new_lines=[]
    for word in final_line:
        new_lines.append(word)

    table_lines=new_lines

    print(F'table_header_text is {table_header_text}')

    whole_table_box=combine_dicts(new_lines)
    header_page=whole_table_box['pg_no']

    if table_header_text:
        new_lines_=[]
        for page in ocr_data:
            if page and page[0]['pg_no'] == header_page:
                for word in page:
                    if whole_table_box['top']-100<=word['top'] and  whole_table_box['bottom']+100>=word['bottom']:
                        # print(f'words is checking here {word}')
                        new_lines_.append(word)

        if new_lines_:
            table_lines=new_lines_

    print(F'table_header_text is {combine_dicts(table_lines)}')

    if not table_header_text:
        headers=group_words_into_columns(table_lines, col_threshold=5)
    else:
        table_header_text=list(table_header_text)
        print(F'table_header_text is {table_header_text}')
        sorted_words = sorted(table_header_text, key=lambda x: len(x.split()), reverse=True)
        headers=[]
        for header in sorted_words:
            words=[word for word in header.split() if re.sub(r'[^a-zA-Z%#]', '', word)]
            found_header=find_accurate_table_header([table_lines],words)
            new_table_lines=[]
            for word in table_lines:
                if found_header and (found_header['left']<=word['left'] and word['right']<=found_header['right']):
                    pass
                else:
                    new_table_lines.append(word)
            table_lines=new_table_lines
            print(f'found_header is {found_header} for the header is {header}')
            headers.append(found_header)

    final_head=[]
    for head in headers:
        if head:
            final_head.append(head)

    return final_head,table_line_words

------------------------------------------------------------------------------------------------------------------------------------------------

def extract_remarks(headers,footers,ocr_word_all):
    try:
        headers=headers['ocrAreas']
    except:
        headers=headers
    footers=[]

    all_head_identifiers=[]
    for head in headers:
        all_head_identifiers.append(combine_dicts(head))
    # print(f" ################# all_head_identifiers",all_head_identifiers)

    base_head={}
    if all_head_identifiers:
        base_head=max(all_head_identifiers, key=lambda w: w["top"])
    # print(f" ################# base_head",base_head)

    all_foot_identifiers=[]
    for foot in footers:
        all_foot_identifiers.append(combine_dicts(foot))
    # print(f" ################# all_foot_identifiers",all_foot_identifiers)

    base_foot={}
    if all_foot_identifiers:
        base_foot=min(all_foot_identifiers, key=lambda w: w["top"])
    # print(f" ################# base_foot",base_foot)

    if not base_head:
        return {},{}

    remarks_ocr_data_temp=[]
    matched_word=''
    end_matcher=False
    start_matcher=False
    for page in ocr_word_all:
        sorted_words = sorted(page, key=lambda x: (x["top"]))
        word_lines=line_wise_ocr_data(sorted_words)
        current_index=-1
        # print(f'############### word_lines for oage {word_lines[0]} are',word_lines)
        for line in word_lines:
            # print(f'############### line is',line)
            current_index=current_index+1
            for word in line:
                base_identifier_word=re.sub(r'[^a-zA-Z ]', '', base_head['word'])
                if base_identifier_word and not start_matcher:
                    start_matcher = is_fuzzy_subsequence(base_identifier_word, word['word'])
                
                    if start_matcher:
                        matched_word=word
                        if len(all_head_identifiers)>1:
                            words=[]
                            valid_start=True
                            print(f'############### word_lines next lines {current_index} is',word_lines[current_index-4:current_index+1])
                            for word_ in word_lines[current_index-4:current_index+1]:
                                for wo in word_:
                                    words.append(wo['word'])

                            if not words:
                                for word_ in word_lines[current_index:current_index+3]:
                                    for wo in word_:
                                        words.append(wo['word'])
                            print(f'############### here words to consider for nextline',words)

                            for ident in all_head_identifiers:
                                if base_head['word'] != ident['word']:
                                    if not is_word_present(ident['word'], words, threshold=0.95):
                                        print(f'############### identifier not found in this line and the ident is',ident)
                                        valid_start=False
                                        break
                            if not valid_start:
                                start_matcher=False
                                continue

                    if start_matcher:
                        print(f'first line strated is {line}')
                        # temp_line=[]
                        # for word_ in line:
                        #     if word == word_:
                        #         continue
                        #     if word not in temp_line:
                        #         temp_line.append(word)
                        if 'Note' not in matched_word['word'].split():
                            line.remove(matched_word)  
                            
                        print(f'first line strated aftere remove start is {line}')
                        start_header=matched_word
                        if line:
                            if line not in remarks_ocr_data_temp:
                                remarks_ocr_data_temp.append(line)
                        break

                if start_matcher and base_foot:
                    end_matcher = is_fuzzy_subsequence(base_foot['word'], word['word'])
                    break

                if start_matcher:
                    if line not in remarks_ocr_data_temp:
                        remarks_ocr_data_temp.append(line)
                    break

            if end_matcher:
                break

    # print(f'############### remarks_ocr_data_temp is',remarks_ocr_data_temp)

    remarks_ocr_data=remarks_ocr_data_temp
    # for temp_line in remarks_ocr_data_temp:
    #     rmk_line=combine_dicts(temp_line)
    #     if check_remark_row(rmk_line['word']):
    #         remarks_ocr_data.append(temp_line)

    # print(f'############### remarks_ocr_data is',remarks_ocr_data)

    for lst in remarks_ocr_data:
        lst.sort(key=lambda x: x["top"])

    if remarks_ocr_data:
        # Sort the outer list based on the smallest "top" value of each inner list
        remarks_ocr_data=sorted(remarks_ocr_data, key=lambda group: (group[0]['pg_no'], group[0]['top']))

    print(f'############### remarks_ocr_data is',remarks_ocr_data)

    Remarks=[]
    start_word=[]
    other_word=[]
    has_start=False
    i=0
    for i in  range(len(remarks_ocr_data)):
        remark_line=sorted(remarks_ocr_data[i], key=lambda x: (x["left"]))
        print(f'############### remark_line is',remark_line)
        for j in range(len(remark_line)):

            if j == len(remark_line)-1 and len(remark_line)>1:
                break
            
            words = remark_line[j]['word']

            if not is_remark_code_present(remark_line[j]['word']):
                continue
            
            has_start=True
            start_word=[remark_line[j]]
            if len(remark_line) == 1:
                other_word=None
            else:
                other_word=remark_line[j+1]
            print(f'############### start_word is',start_word)
            print(f'############### other_word is',other_word)
            break
        if start_word:
            break

        if i>3 and not start_word:
            start_word=remarks_ocr_data[0]
            i=0
            break
    
    if start_word:
        final_remarks={}
        final_high={}
        Remarks.append(start_word)
        print(f'############### Remarks is',Remarks)
        if not other_word:
            flag_stop=False
            prev_bootom=start_word[0]
            for remark_line in remarks_ocr_data[i+1:]:
                remark_line_box=combine_dicts(remark_line)
                for word in remark_line:
                    if start_word[0]['pg_no']!=word['pg_no']:
                        prev_bootom['bottom']=0
                    print(f'############### start_word',start_word[0],word)

                    if prev_bootom['bottom']<word['top']:

                        if abs(prev_bootom['bottom']-word['top'])>50:
                            if not is_remark_code_present(remark_line_box['word']):
                                continue

                        if remark_line not in Remarks:
                            prev_bootom=word
                            Remarks.append(remark_line)

            print(f'############### Remarks is',Remarks)
            
            te=0
            sorted_line = sorted(Remarks[0], key=lambda x: (x["left"]))
            combine_line=combine_dicts(sorted_line)
            prev_length=combine_line['right']-combine_line['left']
            temp_remark=[combine_dicts(Remarks[0])]

            print(f'############### temp_remark is',temp_remark)
            
            for re_line in Remarks[1:]:

                sorted_line = sorted(re_line, key=lambda x: (x["left"]))
                current_line=combine_dicts(sorted_line)
                current_length=current_line['right']-current_line['left']

                print(f'############### current_line is',current_line)
                print(f'############### prev_length is',prev_length)
                print(f'############### current_length is',current_length)

                check_start=False
                if has_start:
                    check_start=is_remark_code_present(current_line['word'])

                if check_start:
                    lines=line_wise_ocr_data(temp_remark)
                    all_words=[]
                    for line in lines:
                        # line[-1]['word']=line[-1]['word']+'//n'
                        all_words.extend(line)
                    final_remarks[str(te+1)+'**']=combine_dicts(all_words)['word']
                    final_high[str(te+1)+'**']=from_highlights(combine_dicts(temp_remark))
                    temp_remark=[current_line]
                    te=te+1
                else:
                    temp_remark.append(current_line)

                prev_length=current_length
                print(f'############### temp_remark is',temp_remark)

            if temp_remark:
                lines=line_wise_ocr_data(temp_remark)
                all_words=[]
                for line in lines:
                    # line[-1]['word']=line[-1]['word']+'//n'
                    all_words.extend(line)
                final_remarks[str(te+1)+'**']=combine_dicts(all_words)['word']
                final_high[str(te+1)+'**']=from_highlights(combine_dicts(temp_remark))

        elif other_word:
            try:
                prev_bootom = start_word['bottom']
                prev_page = start_word['pg_no']
            except Exception as e:
                try:
                    start_word = start_word[0] 
                    prev_bootom = start_word['bottom']
                    prev_page = start_word['pg_no']
                except Exception as e:
                    print(f"the exception is::::{e}")  # or handle differently if needed

            # prev_bootom=start_word['bottom']
            prev_page=start_word['pg_no']
            prev_bootom = start_word['bottom']
            break_flag=False
            for remark_line in remarks_ocr_data[i+1:]:
                if prev_page != remark_line[0]['pg_no']:
                    prev_bootom=remark_line[0]['top']

                remark_line=sorted(remark_line, key=lambda x: x["left"])
                print(f'############### start_word checking in ',remark_line)

                for word in remark_line:

                    if word['height']>20:
                        continue

                    if start_word['right']+5>word['left']>start_word['left']-5 or start_word['right']+5>word['right']>start_word['left']-5 or start_word['right']+5>(word['left']+word['right'])/2>start_word['left']-5:
                        temP_word = word['word'].split()  # Step 1: split into words
                        cleaned_words = [re.sub(r'[^a-zA-Z0-9]', '', word_) for word_ in temP_word if re.sub(r'[^a-zA-Z0-9]', '', word_)]

                        if is_remark_code_present(word['word']):
                            print(f'############### start_word found in ',word)
                            if len(cleaned_words)>1:
                                temp=copy.deepcopy(word)
                                temp['left']=0
                                temp['right']=0
                                temp['word']=cleaned_words[0]
                                print(f'############### modified strat in ',temp)
                                Remarks.append(temp)
                            else:
                                Remarks.append(word)
                            break
                        # elif len(cleaned_words) == 1 and word not in Remarks and (not re.sub(r'[^a-zA-Z]', '', cleaned_words[0]) or cleaned_words[0].isupper()):
                        #     Remarks.append(word)
                    elif word['right']+5>start_word['left']>word['left']-5 or word['right']+5>start_word['right']>word['left']-5 or word['right']+5>(start_word['left']+start_word['right'])/2>word['left']-5:
                        temP_word = word['word'].split()  # Step 1: split into words
                        cleaned_words = [re.sub(r'[^a-zA-Z0-9]', '', word_) for word_ in temP_word if re.sub(r'[^a-zA-Z0-9]', '', word_)]

                        if is_remark_code_present(word['word']):
                            print(f'############### start_word found in ',word)
                            if len(cleaned_words)>1:
                                temp=copy.deepcopy(word)
                                temp['left']=0
                                temp['right']=0
                                temp['word']=cleaned_words[0]
                                print(f'############### modified strat in ',temp)
                                Remarks.append(temp)
                            else:
                                Remarks.append(word)
                            break
                        # elif len(cleaned_words) == 1 and word not in Remarks and (not re.sub(r'[^a-zA-Z]', '', cleaned_words[0]) or cleaned_words[0].isupper()):
                        #     Remarks.append(word)
                    elif word['left']<start_word['left']:
                        temP_word = word['word'].split()  # Step 1: split into words
                        cleaned_words = [re.sub(r'[^a-zA-Z0-9]', '', word_) for word_ in temP_word if re.sub(r'[^a-zA-Z0-9]', '', word_)]

                        if is_remark_code_present(word['word']):
                            print(f'############### start_word found in ',word)
                            if len(cleaned_words)>1:
                                temp=copy.deepcopy(word)
                                temp['left']=0
                                temp['right']=0
                                temp['word']=cleaned_words[0]
                                print(f'############### modified strat in ',temp)
                                Remarks.append(temp)
                            else:
                                Remarks.append(word)
                            break

                prev_bootom=word['bottom']
                prev_page=word['pg_no']

                if break_flag:
                    break
        
            # print(f'############### Remarks is',Remarks)
            print(f'############### Remarks is', Remarks)

            remarks_code = {}
            if Remarks:
                last_bottom = next((r for r in Remarks[:2] if isinstance(r, dict) and 'bottom' in r), None)
                # last_bottom = next((r for r in Remarks[:2] if isinstance(r, dict) and 'bottom' in r), None)
                for i in range(len(Remarks)):
                    current = Remarks[i][0] if isinstance(Remarks[i], list) else Remarks[i]
                    current_top = current.get('top')
                    current_bottom = current.get('bottom')
                    current_page = current.get('pg_no')

                    if len(Remarks) - 1 == i:
                        next_top = 1000
                    else:
                        next_item = Remarks[i + 1][0] if isinstance(Remarks[i + 1], list) else Remarks[i + 1]
                        if next_item.get('pg_no') == current_page:
                            next_top = next_item.get('top', 1000)
                        else:
                            next_top = 1000

                    if isinstance(last_bottom, dict) and last_bottom.get('bottom', 0) > current_top:
                        last_bottom = Remarks[i]

                    print(f'############### current_top is', current_top)
                    print(f'############### current is', current)
                    print(f'############### next_top is', next_top)
                    print(f'############### last_bottom is', last_bottom)

                    code_line = []

                    for remark_data in remarks_ocr_data:

                        print(f'############### lone is',remark_data)

                        if current_page != remark_data[0]['pg_no']:
                            continue

                        top=max(remark_data, key=lambda w: w["top"])
                        left=max(remark_data, key=lambda w: w["left"])

                        # print(f'############### top is',top)
                        if (last_bottom and abs(top['top'] - (last_bottom[0]['bottom'] if isinstance(last_bottom, list) else last_bottom['bottom']) ) > 10 
                            and top['top'] > (last_bottom[0]['bottom'] if isinstance(last_bottom, list) else last_bottom['bottom']) 
                            and code_line):
                            break
  
                        if (last_bottom and (last_bottom[0]['left'] if isinstance(last_bottom, list) else last_bottom['left']) > left['left'] 
                            and code_line):
                            break

                        code_line=[]

                        sorted_data = sorted(remark_data, key=lambda x: (x["left"]))
                        key = Remarks[i][0]['word'] if isinstance(Remarks[i], list) else Remarks[i]['word']
                        if next_top>top['top']>=current_top:
                            for word in sorted_data:
                                if word ['word']== key:
                                    continue
                                code_line.append(word)
                                last_bottom=sorted_data[0]

                        if code_line:
                            if key not in remarks_code:
                                remarks_code[key] = []
                            remarks_code[key].append(combine_dicts(code_line))

                        print(f'############### code_line is',code_line)

                    print(f'############### remarks_code is',remarks_code)

                for remark_code,value in  remarks_code.items(): 
                    temp=combine_dicts(value)   
                    final_remarks[remark_code]=temp['word']
                    final_high[remark_code]=from_highlights(temp)
 
        try:    
            final_high['Remark_default']=from_highlights(start_header)
        except:
            pass

        return final_remarks,final_high
    else:
        return {}, {}

-----------------------------------------------------------------------------------------------------------------------------
def predict_sub_templates(section_identifier,ocr_word_all,ocr_data_all,section_header,process_trained_fields):

    section_heads=[]
    section_format=[]
    if section_header:
        section_heads=section_header['identifiers']
        section_format=section_header['formats']

    try:
        print(f" ################# identifiers['section_identifiers']",section_identifier)
        if not section_identifier:
            return None,None,None,None
        
        start=section_identifier[0]
        # print(f" ################# start",start)
        # end=section_identifier[1]
        try:
            end=section_identifier[1]
        except:
            end=[]
        # print(f" ################# end",end)


        all_identifiers=[]
        other_identifers={}
        for identifiers in start:
            if not identifiers:
                continue
            lines_identifiers=line_wise_ocr_data(identifiers)
            temp_ident=combine_dicts(lines_identifiers[0])
            all_identifiers.append(temp_ident)
            other_identifers[temp_ident['word']]=[]
            for other_ident in lines_identifiers[1:]:
                other_identifers[temp_ident['word']].append(combine_dicts(other_ident)['word'])
        print(f" ################# all_identifiers",all_identifiers)
        # print(f"other identifiers got are {other_identifers}")

        base_identifier=min(all_identifiers, key=lambda w: w["top"])
        print(f" ################# base_identifier",base_identifier)

        all_end_identifiers=[]
        if end:
            for identifiers in end:
                if identifiers:
                    all_end_identifiers.append(combine_dicts(identifiers))
            print(f" ################# all_end_identifiers",all_end_identifiers)

        base_end_identifier={}
        if all_end_identifiers:
            base_end_identifier=max(all_end_identifiers, key=lambda w: w["top"])
            print(f" ################# base_end_identifier",base_end_identifier)

        # Compute distances
        distances = {}
        for word in all_end_identifiers:
            if word != base_identifier and word:
                dist = base_identifier['right']-word['left']
                distances[word["word"]]= dist
        #         print(f" ################# word and dist",word ,dist)
        # print(f" ################ distances",distances)

    except Exception as e:
        print(f"here we have an exception {e}")
        all_identifiers=[]
        other_identifers={}
        base_end_identifier={}
        all_end_identifiers=[]
        for identifiers in section_identifier:
            all_identifiers.append(combine_dicts(identifiers))
        print(f" ################# all_identifiers",all_identifiers)

        base_identifier=min(all_identifiers, key=lambda w: w["top"])
        print(f" ################# base_identifier",base_identifier)

        # Compute distances
        distances = {}
        for word in all_identifiers:
            if word != base_identifier:
                dist = base_identifier['right']-word['left']
                distances[word["word"]]= dist
                print(f" ################# word and dist",word ,dist)
        print(f" ################ distances",distances)

    found_flag=False
    cordinates=[]
    end_point={}

    Claim_countinuation_word=['CONTINUED ON NEXT PAGE']

    try:
        start_page=ocr_word_all[0][0]['pg_no']
    except:
        for page in ocr_word_all:
            for words in page:
                for word in words:
                    start_page=word['pg_no']
    skip_count=0

    for page in ocr_word_all:
        sorted_words = sorted(page, key=lambda x: (x["top"]))
        word_lines=line_wise_ocr_data(sorted_words)
        current_index=-1

        print(f'################ we are at validating word {page[0]["pg_no"]}')

        for line in word_lines:
            current_index=current_index+1

            line_words = [word["word"] for word in line]
            line_words=' '.join(line_words)
            for wo in Claim_countinuation_word:
                if is_fuzzy_subsequence(wo, line_words):
                    skip_count=0
                    break

            for word in line:
                cleaned_word=re.sub(r'[^a-zA-Z]', '', word['word'])
                base_identifier_word=re.sub(r'[^a-zA-Z]', '', base_identifier['word'])
                if base_identifier_word:

                    if end_point and ((end_point['pg_no'] > word['pg_no']) or (end_point['pg_no'] == word['pg_no'] and word['top'] < end_point['bottom'])):
                        continue
                    
                    start_matcher = is_fuzzy_subsequence(base_identifier['word'], word['word'])
                    print(f'################ start_matcher word {word["word"]} is {start_matcher}')

                    similarity_ratio_con_end=0
                    end_matcher=False
                    if base_end_identifier:
                        end_matcher = is_fuzzy_subsequence(base_end_identifier['word'], word['word'])

                    if skip_count >0 and (start_matcher or end_matcher):
                        start_matcher=False
                        end_matcher=False
                        skip_count=skip_count-1

                    if start_matcher:

                        if len(all_identifiers)>1:
                            words=[]
                            valid_start=True
                            for word_ in word_lines[current_index:current_index+5]:
                                for wo in word_:
                                    words.extend(wo['word'].split())
                            print(f'############### here words to consider for nextline',words)

                            for ident in all_identifiers:
                                if base_identifier['word'] != ident['word']:
                                    temp_ids=ident['word'].split()
                                    for temp_id in temp_ids:
                                        if not is_word_present(temp_id, words, threshold=0.95):
                                            print(f'############### identifier not found in this line and the ident is',ident)
                                            valid_start=False
                                            break
                            
                            if not valid_start:
                                continue

                        if cordinates and not end_point and len(cordinates[-1])<3:
                            print(f'############### another line is found but append this start as last end',word)
                            cordinates[-1].extend([word['pg_no'],word['top']])

                        valid=True
                        if other_identifers and len(other_identifers[base_identifier['word']])>0:
                            words=[]
                            for word_ in word_lines[current_index:current_index+5]:
                                for wo in word_:
                                    words.append(wo['word'])
                            print(f'############### here words to consider for nextline',words)
                            for ident in other_identifers[base_identifier['word']]:
                                if not is_word_present(ident, words, threshold=0.95):
                                    print(f'############### identifier not found in this line and the ident is',ident)
                                    valid=False
                                    break

                        if not valid:
                            continue

                        end_point=valid_identifier(ocr_word_all,distances,word)
                        print(f'################ sub template is found at line',word ,end_point)

                        if end_point and len(all_end_identifiers)>1:
                            words=[]
                            valid_end=True
                            ind=0
                            for page_end in ocr_word_all:
                                if end_point['pg_no']== page_end[0]['pg_no']:
                                    word_lines_ed=line_wise_ocr_data(page_end)
                                    for word_ in word_lines_ed:
                                        if ind>5:
                                            break
                                        if end_point['top']<=word_[0]['top']:
                                            for wo in word_:
                                                words.append(wo['word'])
                                            ind=ind+1
                            print(f'############### here words to consider for 1',words)

                            for ident in all_end_identifiers:
                                if base_end_identifier['word'] != ident['word']:
                                    if not is_word_present(ident['word'], words, threshold=0.95):
                                        print(f'############### identifier not found in this line and the ident is',ident)
                                        valid_end=False
                                        break

                            if valid_end:
                                if end_point:
                                    print(f'################ end_point',end_point,'for',word)
                                    cordinates.append([word['pg_no'],word['top'],end_point['pg_no'],end_point['bottom']])
                                
                        elif end_point:
                            print(f'################ end_point',end_point,'for',word)
                            cordinates.append([word['pg_no'],word['top'],end_point['pg_no'],end_point['bottom']])
                                
                        elif not end_point:
                            print(f'################ no end_point',end_point,'for',word)
                            cordinates.append([word['pg_no'],word['top']])
                            print(f'################ cordinates',cordinates)

                    elif end_matcher:

                        print(f'############## validatig end identifier for nextline')

                        words=[]
                        valid_end=True
                        for word_ in word_lines[current_index:current_index+4]:
                            for wo in word_:
                                words.extend(wo['word'].split())
                        print(f'############### here words to consider for nextline',words)

                        for ident in all_end_identifiers:
                            if base_end_identifier['word'] != ident['word']:
                                base_end=ident['word'].split()
                                for end_wo in base_end:
                                    if not is_word_present(end_wo, words, threshold=0.95):
                                        print(f'############### identifier not found in this line and the ident is',ident)
                                        valid_end=False
                                        break

                        if valid_end:
                            if cordinates:
                                if len(cordinates[-1])<3:
                                    print(f'############### another line is found but append this start as last end',word)
                                    cordinates[-1].extend([word['pg_no'],word['bottom']])
                                    continue

                                print(f'################ direct end_point',end_point,'for',word)
                                cordinates.append([cordinates[-1][2],cordinates[-1][3]+1,word['pg_no'],word['bottom']])
                                print(f'################ cordinates',cordinates)
                            else:
                                cordinates.append([start_page,0,word['pg_no'],word['bottom']])
                                print(f'################ cordinates',cordinates)

    last_page=sorted(ocr_data_all[-1], key=lambda x: (x["top"]))
    if cordinates and len(cordinates[-1])<4:
        # print(f'############### we have didnt find any end point in the last so appending last wrd of last page',last_page[-1])
        cordinates[-1].extend([last_page[-1]['pg_no'],last_page[-1]['bottom']])

    print(f'cordinates',cordinates)

    print(f'section ocr satrting here')
    all_sections=[]
    index=-1
    all_headers=[] 
    pre_claim=''
    new_cord=[]
    for cordinate in cordinates:
        index=index+1
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_word_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word_line=sorted(word_line, key=lambda x: (x["pg_no"], x["top"]))
                word=word_line[0]
                if word['bottom'] > end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top']+5 >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    # print(f"start word is {word}")
                    section[word['pg_no']].extend(word_line)
            if stop:
                break
        print(f'one section ending here',section.keys())
        if section_heads:
            section_format_identification=section_format

            if index==0:
                for head in section_heads:
                    detected_header_got=extract_section_header(ocr_pages,head,start_pg)
                    detected_header=copy.deepcopy(detected_header_got)
                    if detected_header:
                        all_headers.extend(detected_header)
                print(f'all_headers here',all_headers)
                if all_headers:
                    temp_section=get_filtered_section(section,section_format_identification)

                    if temp_section:
                        section=temp_section

                    print(f'index 0 here',detected_header)
                    for he in all_headers:
                        if he in section[start_pg]:
                            section[start_pg].remove(he)

                    header_box=combine_dicts(all_headers)
                    print(f'header_box here',header_box)

                    # print(f'section[word[pg_no]] here',section[word['pg_no']])
                    actual_start=combine_dicts(section[start_pg])
                    print(f'actual_start here',actual_start)
                    actual_start=actual_start['top']
                    # print(f'actual_start here',actual_start)
                    second_header_diff=header_box['bottom']-actual_start
                    # print(f'second_header_diff here',second_header_diff)
                    
                    print(f'adding to section {section}')
                    for head in all_headers:
                        print(f'adding to header {head}')
                        if head['pg_no'] in section:
                            print(f'adding to header {head}')
                            section[head['pg_no']].extend(all_headers)
                            break

            else:

                if section and all_headers:
                    header_box=[]

                    temp_section=get_filtered_section(section,section_format_identification)
                    if temp_section:
                        section=temp_section
                        temp_start_pg=list(temp_section.keys())[0]
                    else:
                        temp_start_pg=start_pg

                    temp_headers=copy.deepcopy(all_headers)
                    header_box=combine_dicts(temp_headers)
                    
                    if section[temp_start_pg]:
                        start_cord=combine_dicts(section[temp_start_pg])
                    else:
                        start_cord=combine_dicts(section[start_pg])
                    print(f'start_cord here',start_cord)

                    if start_cord:
                        start_cord=start_cord['top']
                        current_header_diff=header_box['bottom']-start_cord
                        print(f'current_header_diff here',current_header_diff)
                        print(f'second_header_diff here',second_header_diff)
                        overall_diff=current_header_diff-second_header_diff
                        print(f'overall_diff here',overall_diff)
                        
                        for head in temp_headers:
                            if head['pg_no']!= temp_start_pg:
                                head['pg_no']=temp_start_pg
                            head['top']=head['top']-overall_diff
                            head['bottom']=head['bottom']-overall_diff

                        # print(f'section_headers after modfication here',detected_header)
                        print(f'adding to section {section}')
                        for head in temp_headers:
                            print(f'adding to header {head}')
                            if head['pg_no'] in section:
                                section[head['pg_no']].extend(temp_headers)
                                break

        print(f' -----> section here is ',section)
        
        # try:
        claim_id=check_claim(list(section.values()),process_trained_fields)
        # except Exception as e:
        #     print(f'here we have an exception is {e}')
        #     claim_id=''
        print(f'claim_id got is {claim_id}')
        print(f'pre_claim got is {pre_claim}')
        if pre_claim and pre_claim ==  claim_id:
            print(f'claim_id got is {all_sections[-1]}')
            print(f'pre_claim got is {section}')
            pre_claim=claim_id
            combined = {}
            for k in set(all_sections[-1]) | set(section):   # union of keys
                combined[k] = all_sections[-1].get(k, []) + section.get(k, [])
            all_sections[-1]=combined
            new_cord[-1][2]=cordinate[2]
            new_cord[-1][3]=cordinate[3]
        else:
            pre_claim=claim_id
            all_sections.append(section)
            new_cord.append(cordinate)

    print(f'New cords formed are {new_cord}')
    cordinates=new_cord

    reamark_cordinates=[]
    for i in range(len(cordinates)):

        current=cordinates[i]
        if i == len(cordinates)-1:
            next_=[last_page[-1]['pg_no'],last_page[-1]['bottom']]
        else:
            next_=cordinates[i+1]
        merged = current[:2] + next_[:2] 
        reamark_cordinates.append(merged)

    remarks_section_ocr=[]
    for cordinate in reamark_cordinates:
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_word_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word=word_line[0]
                if word['top'] >= end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top'] >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    section[word['pg_no']].extend(word_line)
            if stop:
                break
        # print(f'one section ending here',section.keys())
        for head in section_heads:
            detected_header=extract_section_header(ocr_pages,head,start_pg)
            # print(f'section_headers here',detected_header)
            for head in detected_header:
                if head['pg_no'] in section:
                    section[head['pg_no']].extend(detected_header)
                    break
        remarks_section_ocr.append(section)


    print(f'section ocr 2 satrting here')
    all_headers=[]  
    all_ocr_sections=[]
    index=-1
    for cordinate in cordinates:
        index=index+1
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_data_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            if not page:
                continue
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word_line=sorted(word_line, key=lambda x: (x["pg_no"], x["top"]))
                word=word_line[0]
                if word['bottom'] > end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top']+5 >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    # print(f"start word is {word}")
                    section[word['pg_no']].extend(word_line)
            if stop:
                break
        # print(f'one section ending here',section.keys())
        if section_heads:
            section_format_identification=section_format

            if index==0:
                for head in section_heads:
                    detected_header_got=extract_section_header(ocr_pages,head,start_pg)
                    detected_header=copy.deepcopy(detected_header_got)
                    if detected_header:
                        all_headers.extend(detected_header)
                print(f'all_headers here',all_headers)
                if all_headers:
                    temp_section=get_filtered_section(section,section_format_identification)

                    if temp_section:
                        section=temp_section

                    print(f'index 0 here',detected_header)
                    for he in all_headers:
                        if he in section[start_pg]:
                            section[start_pg].remove(he)

                    header_box=combine_dicts(all_headers)
                    print(f'header_box here',header_box)

                    # print(f'section[word[pg_no]] here',section[word['pg_no']])
                    actual_start=combine_dicts(section[start_pg])
                    print(f'actual_start here',actual_start)
                    actual_start=actual_start['top']
                    # print(f'actual_start here',actual_start)
                    second_header_diff=header_box['bottom']-actual_start
                    # print(f'second_header_diff here',second_header_diff)
                    
                    for head in all_headers:
                        if head['pg_no'] in section:
                            section[head['pg_no']].extend(all_headers)
                            break

            else:
            
                if section and all_headers:
                    header_box=[]

                    temp_section=get_filtered_section(section,section_format_identification)
                    if temp_section:
                        section=temp_section
                        temp_start_pg=list(temp_section.keys())[0]
                    else:
                        temp_start_pg=start_pg

                    temp_headers=copy.deepcopy(all_headers)
                    header_box=combine_dicts(temp_headers)
                    if section[temp_start_pg]:
                        start_cord=combine_dicts(section[temp_start_pg])
                    else:
                        start_cord=combine_dicts(section[start_pg])
                    print(f'start_cord here',start_cord)

                    if start_cord:
                        start_cord=start_cord['top']
                        current_header_diff=header_box['bottom']-start_cord
                        print(f'current_header_diff here',current_header_diff)
                        print(f'second_header_diff here',second_header_diff)
                        overall_diff=current_header_diff-second_header_diff
                        print(f'overall_diff here',overall_diff)
                        
                        for head in temp_headers:
                            if head['pg_no']!= temp_start_pg:
                                head['pg_no']=temp_start_pg
                            head['top']=head['top']-overall_diff
                            head['bottom']=head['bottom']-overall_diff

                        # print(f'section_headers after modfication here',detected_header)
                        for head in temp_headers:
                            if head['pg_no'] in section:
                                section[head['pg_no']].extend(temp_headers)
                                break
                        
        all_ocr_sections.append(section)
                
    return all_sections,cordinates,all_ocr_sections,remarks_section_ocr

-----------------------------------------------------------------------------------------------------------------------------------------------

def predict_sub_sub_templates(section_identifier,ocr_word_all,ocr_data_all):
    
    print(f" ################# identifiers['section_identifiers']",section_identifier)
    if not section_identifier:
        return None,None,None,None
    
    start=section_identifier

    all_identifiers=[]
    other_identifers={}
    for identifiers in start:
        if not identifiers:
            continue
        lines_identifiers=line_wise_ocr_data(identifiers)
        temp_ident=combine_dicts(lines_identifiers[0])
        all_identifiers.append(temp_ident)
        other_identifers[temp_ident['word']]=[]
        for other_ident in lines_identifiers[1:]:
            other_identifers[temp_ident['word']].append(combine_dicts(other_ident)['word'])
    print(f" ################# all_identifiers",all_identifiers)

    base_identifier=min(all_identifiers, key=lambda w: w["top"])
    print(f" ################# base_identifier",base_identifier)

    cordinates=[]
    end_point={}

    for page in ocr_word_all:
        sorted_words = sorted(page, key=lambda x: (x["top"]))
        word_lines=line_wise_ocr_data(sorted_words)
        current_index=-1
        for line in word_lines:
            current_index=current_index+1
            for word in line:
                base_identifier_word=re.sub(r'[^a-zA-Z]', '', base_identifier['word'])
                if base_identifier_word:

                    if end_point and ((end_point['pg_no'] > word['pg_no']) or (end_point['pg_no'] == word['pg_no'] and word['top'] < end_point['bottom'])):
                        continue
                    
                    # start_matcher = is_fuzzy_subsequence(base_identifier['word'], word['word'])

                    match_ratio = SequenceMatcher(None, word['word'], base_identifier['word']).ratio()
                    
                    if match_ratio >= 0.85:
                        start_matcher=True
                    else:
                        start_matcher=False

                    if start_matcher:

                        if len(all_identifiers)>1:
                            words=[]
                            valid_start=True
                            for word_ in word_lines[current_index:current_index+4]:
                                for wo in word_:
                                    words.extend(wo['word'].split())
                            print(f'############### here words to consider for nextline',words)

                            for ident in all_identifiers:
                                if base_identifier['word'] != ident['word']:
                                    temp_ids=ident['word'].split()
                                    for temp_id in temp_ids:
                                        if not is_word_present(temp_id, words, threshold=0.95):
                                            print(f'############### identifier not found in this line and the ident is',ident)
                                            valid_start=False
                                            break
                            
                            if not valid_start:
                                continue

                        if cordinates and not end_point and len(cordinates[-1])<3:
                            print(f'############### another line is found but append this start as last end',word)
                            cordinates[-1].extend([word['pg_no'],word['top']])

                        valid=True
                        if other_identifers and len(other_identifers[base_identifier['word']])>0:
                            words=[]
                            for word_ in word_lines[current_index:current_index+4]:
                                for wo in word_:
                                    words.append(wo['word'])
                            print(f'############### here words to consider for nextline',words)
                            for ident in other_identifers[base_identifier['word']]:
                                if not is_word_present(ident, words, threshold=0.95):
                                    print(f'############### identifier not found in this line and the ident is',ident)
                                    valid=False
                                    break

                        if not valid:
                            continue

                        elif end_point:
                            print(f'################ end_point',end_point,'for',word)
                            cordinates.append([word['pg_no'],word['top'],end_point['pg_no'],end_point['bottom']])
                                
                        elif not end_point:
                            print(f'################ no end_point',end_point,'for',word)
                            cordinates.append([word['pg_no'],word['top']])
                            
    print(f'################ cordinates',cordinates)
    for page in reversed(ocr_word_all):
        if page:  # non-empty list
            last_page_words = page
            break

    # Sort if there are words
    last_page = sorted(last_page_words, key=lambda x: x["top"]) if last_page_words else []

    print(f'################ last_page',last_page)
    if cordinates and len(cordinates[-1])<4:
        # print(f'############### we have didnt find any end point in the last so appending last wrd of last page',last_page[-1])
        cordinates[-1].extend([last_page[-1]['pg_no'],last_page[-1]['bottom']])

    # print(f'cordinates',cordinates)
    reamark_cordinates=[]
    for i in range(len(cordinates)):

        current=cordinates[i]
        if i == len(cordinates)-1:
            next_=[last_page[-1]['pg_no'],last_page[-1]['bottom']]
        else:
            next_=cordinates[i+1]
        merged = current[:2] + next_[:2] 
        reamark_cordinates.append(merged)

    remarks_section_ocr=[]
    for cordinate in reamark_cordinates:
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_word_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word=word_line[0]
                if word['top'] >= end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top'] >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    section[word['pg_no']].extend(word_line)
            if stop:
                break

        remarks_section_ocr.append(section)

    print(f'section ocr satrting here')
    all_sections=[]
    index=-1
    all_headers=[] 
    for cordinate in cordinates:
        index=index+1
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_word_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word_line=sorted(word_line, key=lambda x: (x["pg_no"], x["top"]))
                word=word_line[0]
                if word['bottom'] > end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top']+5 >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    # print(f"start word is {word}")
                    section[word['pg_no']].extend(word_line)
            if stop:
                break
        # print(f'one section ending here',section.keys())
        all_sections.append(section)


    print(f'section ocr 2 satrting here')
    all_headers=[]  
    all_ocr_sections=[]
    index=-1
    for cordinate in cordinates:
        index=index+1
        # print(f'cordinate',cordinate)
        section={}
        start_pg=cordinate[0]
        start_cord=cordinate[1]
        end_pg=cordinate[2]
        end_cord=cordinate[3]
        ocr_pages=[]
        for ocr_word in ocr_data_all:
            if not ocr_word:
                continue
            if start_pg <= ocr_word[0]['pg_no'] <= end_pg:
                ocr_pages.append(ocr_word)
            if ocr_word[0]['pg_no']>end_pg:
                break
        stop=False
        start=False
        for page in ocr_pages:
            if not page:
                continue
            word_lines=line_wise_ocr_data(page)
            section[page[0]['pg_no']]=[]
            for word_line in word_lines:
                word_line=sorted(word_line, key=lambda x: (x["pg_no"], x["top"]))
                word=word_line[0]
                if word['bottom'] > end_cord and end_pg == word['pg_no']:
                    # print(f"stoping word is {word}")
                    stop=True 
                    break
                if word['top']+5 >= start_cord and start_pg == word['pg_no'] and not start:
                    start=True
                    
                if start:
                    # print(f"start word is {word}")
                    section[word['pg_no']].extend(word_line)
            if stop:
                break

        all_ocr_sections.append(section)
                
    return all_sections,cordinates,all_ocr_sections,remarks_section_ocr


------------------------------------------------------------------------------------------------------------------------------
def line_wise_ocr_data(words):
    """
    Forms the values in each line and creates line-wise OCR data.

    Args:
        words: List of dictionaries containing OCR data.

    Returns:
        list: List of lists where each inner list represents words on the same horizontal line.
    """
    ocr_word = []

    # Sort words based on their 'top' coordinate
    sorted_words = sorted(filter(lambda x: isinstance(x, dict) and "pg_no" in x and "top" in x, words), key=lambda x: (x["pg_no"], x["top"]))

    # sorted_words = sorted(words, key=lambda x: (x["pg_no"], x["top"]))

    # Group words on the same horizontal line
    line_groups = []
    current_line = []

    for word in sorted_words:
        if not current_line:
            # First word of the line
            current_line.append(word)
        else:
            diff = abs(word["top"] - current_line[0]["top"])
            if diff < 5:
                # Word is on the same line as the previous word
                current_line.append(word)
            else:
                # Word is on a new line
                current_line=sorted(current_line, key=lambda x: x["left"])
                line_groups.append(current_line)
                current_line = [word]

    # Add the last line to the groups
    if current_line:
        current_line=sorted(current_line, key=lambda x: x["left"])
        line_groups.append(current_line)
        
    for line in line_groups:
        line_words = [word["word"] for word in line]
        # print(" ".join(line_words))

    return line_groups


-------------------------------------------------------------------------------------------------------------
def find_extra_headers(second_headers,ocr_data):

    found_extra_headers={}

    for extra_head in second_headers:

        print(f'finding extra header is {extra_head}')

        ocr=extra_head['croppedOcrAreas']
        mapped_head=extra_head['value']

        words=[word['word'] for word in ocr if re.sub(r'[^a-zA-Z%#]', '', word['word'])]
        print(f'header words aree {words}')

        possible_header=find_accurate_table_header(ocr_data,words)

        if possible_header:
            found_extra_headers[mapped_head]=possible_header

    print(f'final extra header groups are {found_extra_headers}')

    
    second_header_box= combine_dicts(list(found_extra_headers.values()))

    return found_extra_headers,second_header_box


---------------------------------------------------------------------------------------------------------------------------------------
def predict_paragraph(para_fields,ocr_word_all):

    para_field,para_high={},{}

    for field,section_identifier in para_fields.items():

        print(f" ################# identifiers['section_identifiers']",section_identifier)
        if not section_identifier:
            return None,None,None,None
        
        start=section_identifier[0]
        print(f" ################# start",start)

        start_idenitfier={}
        if start:
            start_idenitfier=combine_dicts(start)
            print(f" ################# start_identifiers",start_idenitfier)

        if not start:
            continue

        try:
            end=section_identifier[1]
        except:
            end=[]
        print(f" ################# end",end)
        end_identifiers={}
        if end:
            end_identifiers=combine_dicts(end)
            print(f" ################# end_identifiers",end_identifiers)

        start_matcher=False
        end_matcher=False
        stop=False
        needed_lines=[]
        for page in ocr_word_all:
            sorted_words = sorted(page, key=lambda x: (x["top"]))
            word_lines=line_wise_ocr_data(sorted_words)
            current_index=-1
            for line in word_lines:
                current_index=current_index+1
                for word in line:
                    cleaned_word=re.sub(r'[^a-zA-Z]', '', word['word'])
                    base_identifier_word=re.sub(r'[^a-zA-Z]', '', start_idenitfier['word'])
                    if base_identifier_word and not start_matcher:
                        start_matcher = is_fuzzy_subsequence(base_identifier_word, cleaned_word)
                        if start_matcher:
                            print(f" ################# start_matcher found at",word['word'])
                            break
                    
                    base_end_identifier_word=re.sub(r'[^a-zA-Z]', '', end_identifiers['word'])
                    if base_end_identifier_word:
                        end_matcher = is_fuzzy_subsequence(base_end_identifier_word,cleaned_word)
                        if end_matcher:
                            print(f" ################# end_matcher found at",word['word'])
                            break

                if start_matcher and not end_matcher:
                    needed_lines.extend(line)
                elif start_matcher and end_matcher:
                    needed_lines.extend(line)
                    stop=True

                if stop:
                    break
            
            if stop:
                break
            
        print(f" ################# found needed_lines are",needed_lines)

        if needed_lines:
            needed_para=''
            needed_para_high=[]
            needed_lines=line_wise_ocr_data(needed_lines)
            for line in needed_lines:
                sorted_para_line = sorted(line, key=lambda x: (x["right"]))
                for wor in sorted_para_line:
                    needed_para=needed_para+' '+wor['word']
                needed_para_high.extend(line)
            print(f" ################# found needed_para is",needed_para)
            para_field[field]=needed_para
            para_high[field]=from_highlights(combine_dicts(needed_para_high))

    return para_field,para_high


-----------------------------------------------------------------------------------------------------------------------


You can discuss Up to predict graph in ionic extraction now tell how to draw the diagram







