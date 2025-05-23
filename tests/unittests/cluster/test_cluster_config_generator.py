import os
import tempfile

import pytest
import yaml

from autogluon.cloud.cluster import ClusterConfigGenerator, RayAWSClusterConfigGenerator
from autogluon.cloud.cluster.constants import (
    AUTH,
    AVAILABLE_NODE_TYPES,
    BLOCK_DEVICE_MAPPINGS,
    DOCKER,
    EBS,
    IMAGE,
    IMAGE_ID,
    INITIALIZATION_COMMANDS,
    INSTANCE_TYPE,
    KEY_NAME,
    MAX_WORKERS,
    MIN_WORKERS,
    NODE_CONFIG,
    PROVIDER,
    REGION,
    SSH_PRIVATE_KEY,
    VOLUME_SIZE,
)
from autogluon.cloud.utils.aws_utils import get_latest_amazon_linux_ami


def _create_config_file(config):
    if isinstance(config, str):
        with open(config, "w") as yaml_file:
            yaml.safe_dump({"foo": "bar"}, yaml_file)


@pytest.mark.parametrize("config_generator", [RayAWSClusterConfigGenerator])
@pytest.mark.parametrize("config", [None, {"foo": "bar"}, "dummy.yaml"])
def test_generate_config(config_generator, config):
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        _create_config_file(config)
        region = "us-west-2"
        config_generator: ClusterConfigGenerator = config_generator(config, region=region)
        assert isinstance(config_generator.config, dict)
        if config is None:
            assert config_generator.config[PROVIDER][REGION] == region


@pytest.mark.parametrize("config", [None, {"foo": "bar"}, "dummy.yaml"])
def test_update_ray_aws_cluster_config(config):
    latest_ami = get_latest_amazon_linux_ami()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        _create_config_file(config)
        config_generator = RayAWSClusterConfigGenerator(config, use_latest_ami=False)
        # Test update
        dummy_config = {"cluster_name": "foo"}
        config_generator.update_config(dummy_config)
        assert config_generator.config["cluster_name"] == "foo"
        config_generator.update_config(config_generator.default_config_file)
        config_generator.update_config(
            instance_type="foo",
            instance_count=2,
            volumes_size=2,
            ami=latest_ami,
            custom_image_uri="bar",
            ssh_key_path="dummy.pem",
            initialization_commands=["abc"],
        )
        node = config_generator.config[AVAILABLE_NODE_TYPES]["worker"]
        node_config = node[NODE_CONFIG]
        assert node_config[INSTANCE_TYPE] == "foo"
        assert config_generator.config[MAX_WORKERS] == 1 and node[MIN_WORKERS] == 1
        assert node_config[BLOCK_DEVICE_MAPPINGS][0][EBS][VOLUME_SIZE] == 2
        assert config_generator.config[DOCKER][IMAGE] == "bar"
        assert config_generator.config[AUTH][SSH_PRIVATE_KEY] == os.path.abspath("dummy.pem")
        assert node_config[IMAGE_ID] == latest_ami
        assert node_config[KEY_NAME] == "dummy"
        assert config_generator.config[INITIALIZATION_COMMANDS] == ["abc"]
        config = config_generator.config
        # Test save
        saved_config = os.path.join(temp_dir, "config.yaml")
        config_generator.save_config(saved_config)
        config_generator = RayAWSClusterConfigGenerator(saved_config)
        assert config == config_generator.config
