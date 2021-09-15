events = ['Darfield_MS_7.2', 'Darfield_AS_5.8', 'Darfield_AS_5.5']

rule all:
    input:
        expand("/home/sysop/data/{event}/{event}.sqlite3", event=events)

rule waveform:
    input:
        "/home/sysop/data/{event}/{event}.json"
    output:
        "/home/sysop/data/{event}/{event}.ms"
    shell:
        "./waveformdl.py -e {input} -o /home/sysop/data/{wildcards.event}"
        
rule inventory:
    input:
        inv="/home/sysop/data/complete.xml",
        wave="/home/sysop/data/{event}/{event}.ms"
    output:
        "/home/sysop/data/{event}/{event}.xml"
    shell:
        "./event_inventory.py {input.wave} -i {input.inv} "
        "> {output}"

rule select:
    input:
        inv="/home/sysop/data/{event}/{event}.xml",
        wave="/home/sysop/data/{event}/{event}.ms"
    output:
        "/home/sysop/data/{event}/{event}_nocolloc.ms"
    shell:
        "./select_traces.py {input.wave} -i {input.inv}" 
        "> {output}"
       
rule bindings:
    input:
        "/home/sysop/data/{event}/{event}_nocolloc.ms"
    output:
        touch("/home/sysop/data/{event}/{event}_nocolloc_bindings/bindingstask.done"),
    shell:
        "./event_bindings.py {input} -r /home/sysop/data/{wildcards.event}"
        
rule database:
    input:
        bindings="/home/sysop/data/{event}/{event}_nocolloc_bindings/",
        inventory="/home/sysop/data/{event}/{event}.xml"
    output:
        "/home/sysop/data/{event}/{event}.sqlite3"
    shell:
        "./playback_db_setup.sh {wildcards.event} {input.inventory} {input.bindings}"
        
rule playback:
    input:
        "/home/sysop/data/{event}/{event}_nocolloc.ms"
    output:
        touch("/home/sysop/data/{event}/temp/playback.done"),
    shell:
        "./docker_playback.sh {wildcards.event} {input}"
