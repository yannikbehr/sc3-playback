import os

EVENTS = ['Darfield_MS_7.2', 'Darfield_AS_5.8', 'Darfield_AS_5.5',
          'Wanaka_5.8', 'Arthurs_Pass_6.0']
          
DATADIR = '/home/sysop/data'

rule all:
    input:
        expand(os.path.join(DATADIR, "{event}/temp/plotting.done"), event=EVENTS)

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
        directory("/home/sysop/data/{event}/{event}_nocolloc_bindings"),
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

rule config:
    params:
        templd=os.path.join(DATADIR, 'sc3_config_templates'),
        configd=os.path.join(DATADIR, '{event}/dot_seiscomp3')
    output:
        directory(os.path.join(DATADIR, '{event}/dot_seiscomp3'))
    shell:
        "./gen_config.py {params.templd} {params.configd}"
        
rule playback:
    input:
        waveforms="/home/sysop/data/{event}/{event}_nocolloc.ms",
        database="/home/sysop/data/{event}/{event}.sqlite3",
        config=os.path.join(DATADIR, '{event}/dot_seiscomp3')
    output:
        directory("/home/sysop/data/{event}/temp_data/")
    shell:
        "./rcet_playback.sh {input.waveforms} {input.database} {input.config}"

rule gif:
    input:
        finderd=os.path.join(DATADIR, "{event}/temp_data"),
        configd=os.path.join(DATADIR, "{event}/dot_seiscomp3")
    params:
        workdir=os.path.join(DATADIR,'{event}')
    output:
        touch(os.path.join(DATADIR, '{event}/temp/plotting.done'))
    shell:
        "./finder2gif --datadir {params.workdir} {input.configd}/finder_geonet.config {input.finderd}"