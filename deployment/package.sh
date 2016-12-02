#!/bin/sh

out_dir=velum/output/velum
mkdir -p ${out_dir}

tar -cf ${out_dir}/velum.tar python_common/*.py --exclude=*.pyc --exclude=*test* \
python_common/geocoding \
velum/*.py velum/common velum/model velum/proxy_import velum/proxy_manager

# Add run.sh to the top level of the tar file
current_dir=`pwd`
cd velum/deployment
tar -rf ${current_dir}/${out_dir}/velum.tar run.sh geopyplus.cfg
cd ${current_dir}


cp velum/deployment/debian_env_setup.sh ${out_dir}/
