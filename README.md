# f0-assemble

Extracts contents from phones with F0 F0 structure.

## assemble.py

Extracts raw chunks from structure, concatening them in order of their ID.

## appsys.py

Extracts APP system within the structure of this phone. Option -a needs to be specified because the chunk ID that starts this system varies by phone model.

Example of known chunk IDs per model:
- J-SH07: 5504
- J-SH08: 5504
- J-SH010: 6355

Note: the app system header is located one chunk before actual contents (e.g. 5503 for J-SH07)