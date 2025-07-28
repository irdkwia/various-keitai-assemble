# various-keitai-assemble

Extracts contents from some keitai phones. All scripts arguments can be seen with option -h

## assemble_f0.py

Extracts raw chunks from F0 F0 structure, concatening them in order of their ID.

## appsys_f0.py

Extracts APP system within the structure of F0 F0 phones. Option -a needs to be specified because the chunk ID that starts this system varies by phone model.

Example of known chunk IDs per model:
- J-SH07: 5504
- J-SH08: 5504
- J-SH010: 6355

Note: the app system header is located one chunk before actual contents (e.g. 5503 for J-SH07)

## assemble_sh704i_d904i.py

Rearrange dump from SH704i / D904i FTLs.

## assemble_sh900i.py

Extracts raw chunks from SH900i.

## assemble_soffs.py

Rearrange dump from SoFFS FTLs.

## assemble_vsh.py

Extracts raw chunks from Vodafone SH FTLs.