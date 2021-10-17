import os

EVENTS = ['Darfield_MS_7.2', 'Darfield_AS_5.8', 'Darfield_AS_5.5',
          'Wanaka_5.8', 'Arthurs_Pass_6.0', 'Kaikoura_MS_7.8']
          
DATADIR = '/home/sysop/data'

rule all:
    input:
        expand(os.path.join(DATADIR, "{event}/.plotting.done"), event=EVENTS)

rule waveform:
    input:
        os.path.join(DATADIR, "{event}/{event}.json")
    output:
        os.path.join(DATADIR, "{event}/{event}_raw.ms")
    shell:
        "./waveformdl.py -e {input} {output}"
        
rule inventory:
    input:
        inv=os.path.join(DATADIR, "complete.xml"),
        wave=os.path.join(DATADIR, "{event}/{event}_raw.ms")
    output:
        os.path.join(DATADIR, "{event}/{event}.xml")
    shell:
        "./event_inventory.py {input.wave} -i {input.inv} "
        "> {output}"

rule select:
    input:
        inv=os.path.join(DATADIR, "{event}/{event}.xml"),
        wave=os.path.join(DATADIR, "{event}/{event}_raw.ms")
    output:
        os.path.join(DATADIR, "{event}/{event}.ms")
    shell:
        "./select_traces.py {input.wave} -i {input.inv} -p -c -t" 
        "> {output}"
       
rule bindings:
    input:
        os.path.join(DATADIR, "{event}/{event}.ms")
    output:
        directory(os.path.join(DATADIR, "{event}/{event}_bindings")),
    shell:
        "./event_bindings.py {input} -r /home/sysop/data/{wildcards.event}"
        
rule database:
    input:
        bindings=os.path.join(DATADIR, "{event}/{event}_bindings/"),
        inventory=os.path.join(DATADIR, "{event}/{event}.xml")
    output:
        os.path.join(DATADIR, "{event}/{event}.sqlite3")
    shell:
        "./playback_db_setup.sh {wildcards.event} {input.inventory} {input.bindings}"

rule config:
    input:
        os.path.join(DATADIR, '{event}/{event}.xml')
    params:
        templd=os.path.join(DATADIR, 'sc3_config_templates'),
        configd=os.path.join(DATADIR, '{event}/dot_seiscomp3')
    output:
        directory(os.path.join(DATADIR, '{event}/dot_seiscomp3'))
    shell:
        "./gen_config.py {input} {params.templd} {params.configd}"
        
rule playback:
    input:
        waveforms=os.path.join(DATADIR, "{event}/{event}.ms"),
        database=os.path.join(DATADIR, "{event}/{event}.sqlite3"),
        config=os.path.join(DATADIR, '{event}/dot_seiscomp3')
    output:
        directory(os.path.join(DATADIR, "{event}/temp_data/")),
        directory(os.path.join(DATADIR, "{event}/temp/")),
        os.path.join(DATADIR, '{event}/temp/calculated_mask.nc')
    shell:
        "./rcet_playback.sh {input.waveforms} {input.database} {input.config}"

rule plotmask:
    input:
        mask=os.path.join(DATADIR, '{event}/temp/calculated_mask.nc'),
        inventory=os.path.join(DATADIR, "{event}/{event}.xml")
    params:
        outdir=os.path.join(DATADIR, '{event}')
    output:
        os.path.join(DATADIR, '{event}/finder_mask.png')
    shell:
        "./plot_mask.py {input.mask} {input.inventory} {params.outdir}"

rule gif:
    input:
        finderd=os.path.join(DATADIR, "{event}/temp_data"),
        configd=os.path.join(DATADIR, "{event}/dot_seiscomp3")
    params:
        workdir=os.path.join(DATADIR,'{event}')
    output:
        directory(os.path.join(DATADIR, '{event}', 'tmp_finder_gif')),
        touch(os.path.join(DATADIR, '{event}/.plotting.done'))
    shell:
        "./finder2gif --datadir {params.workdir} {input.configd}/finder_geonet.config {input.finderd}"