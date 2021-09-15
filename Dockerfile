FROM sedeew/sed-addons 

LABEL maintainer="y.behr@gns.cri.nz"

RUN apt-get -q update && \
    apt-get install -yq --no-install-recommends \
    gmt-gshhg \
    locales && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen

ENV WORK_DIR=/home/sysop/ \
    INSTALL_DIR=/opt/seiscomp3 

# conda-forge setup
ARG conda_version="4.9.2"
ARG miniforge_patch_number="7"
ARG miniforge_arch="x86_64"
ARG miniforge_python="Mambaforge"

# Miniforge archive to install
ARG miniforge_version="${conda_version}-${miniforge_patch_number}"
# Miniforge installer
ARG miniforge_installer="${miniforge_python}-${miniforge_version}-Linux-${miniforge_arch}.sh"
# Miniforge checksum
ARG miniforge_checksum="5a827a62d98ba2217796a9dc7673380257ed7c161017565fba8ce785fb21a599"

# Configure environment
ENV CONDA_DIR=/opt/conda \
    HOME=/home/sysop \
    SHELL=/bin/bash \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8
ENV PATH=$CONDA_DIR/bin:$PATH \
    CONDA_VERSION="${conda_version}" \
    MINIFORGE_VERSION="${miniforge_version}"

# Enable prompt color in the skeleton .bashrc before creating the default D_USER
# hadolint ignore=SC2016
RUN sed -i 's/^#force_color_prompt=yes/force_color_prompt=yes/' /etc/skel/.bashrc && \
   # Add call to conda init script see https://stackoverflow.com/a/58081608/4413446
   echo 'eval "$(command conda shell.bash hook 2> /dev/null)"' >> /etc/skel/.bashrc 

# Copy a script that we will use to correct permissions after running certain commands
COPY fix-permissions /usr/local/bin/fix-permissions
RUN chmod a+rx /usr/local/bin/fix-permissions

RUN mkdir -p $CONDA_DIR && \
    chown sysop:$GROUP_ID $CONDA_DIR && \
    chmod g+w /etc/passwd && \
    fix-permissions $HOME && \
    fix-permissions $CONDA_DIR

ARG PYTHON_VERSION=default
WORKDIR /tmp

# Prerequisites installation: conda, mamba, pip, tini
RUN wget --quiet "https://github.com/conda-forge/miniforge/releases/download/${miniforge_version}/${miniforge_installer}" && \
    echo "${miniforge_checksum} *${miniforge_installer}" | sha256sum --check && \
    /bin/bash "${miniforge_installer}" -f -b -p $CONDA_DIR && \
    rm "${miniforge_installer}" && \
    # Conda configuration see https://conda.io/projects/conda/en/latest/configuration.html
    echo "conda ${CONDA_VERSION}" >> $CONDA_DIR/conda-meta/pinned && \
    conda config --system --set auto_update_conda false && \
    conda config --system --set show_channel_urls true && \
    if [ ! $PYTHON_VERSION = 'default' ]; then conda install --yes python=$PYTHON_VERSION; fi && \
    conda list python | grep '^python ' | tr -s ' ' | cut -d '.' -f 1,2 | sed 's/$/.*/' >> $CONDA_DIR/conda-meta/pinned && \
    conda install --quiet --yes \
    "conda=${CONDA_VERSION}" \
    'pip' \
    'tini=0.18.0' && \
    conda update --all --quiet --yes && \
    conda list tini | grep tini | tr -s ' ' | cut -d ' ' -f 1,2 >> $CONDA_DIR/conda-meta/pinned && \
    conda clean --all -f -y && \
    rm -rf /home/$D_USER/.cache/yarn && \
    fix-permissions $CONDA_DIR && \
    fix-permissions /home/sysop

USER sysop
WORKDIR $WORK_DIR

### SeisComp3 settings ###
ENV SEISCOMP_ROOT=/opt/seiscomp3 PATH=/opt/seiscomp3/bin:$PATH \
    LD_LIBRARY_PATH=/opt/seiscomp3/lib:$LD_LIBRARY_PATH \
    PYTHONPATH=/opt/seiscomp3/lib/python:$PYTHONPATH \
    MANPATH=/opt/seiscomp3/share/man:$MANPATH \
    LC_ALL=C

# Setup SeisComP3 + seedlink
ADD sc3_config.cfg .
RUN seiscomp --stdin setup <sc3_config.cfg \
    && mkdir -p /opt/seiscomp3/var/lib/seedlink \
    && mkdir -p /opt/seiscomp3/var/run/seedlink \
    && mkfifo -m=666 /opt/seiscomp3/var/run/seedlink/mseedfifo \
    && seiscomp print env >.bash_aliases    

VOLUME ["/home/sysop/data"]
VOLUME ["/home/sysop/sds"]
VOLUME ["/home/sysop/sc3-playback"]
