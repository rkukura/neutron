# Copyright 2015 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

"""ml2_binding_cleanup

Revision ID: 590306394d9f
Revises: 20c469a5f920
Create Date: 2015-03-24 16:07:10.280753

"""

# revision identifiers, used by Alembic.
revision = '590306394d9f'
down_revision = '20c469a5f920'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('ml2_port_binding_results',
                    sa.Column('port_id',
                              sa.String(length=36),
                              nullable=False),
                    sa.Column('host',
                              sa.String(length=255),
                              nullable=False),
                    sa.Column('vif_type',
                              sa.String(length=64),
                              nullable=False),
                    sa.Column('vif_details',
                              sa.String(length=4095),
                              server_default='',
                              nullable=False),
                    sa.ForeignKeyConstraint(['port_id'],
                                            ['ports.id'],
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('port_id',
                                            'host'))

    # TODO(rkukura): Copy data from ml2_[dvr_]port_bindings columns
    # being dropped to ml2_port_binding_results.

    op.drop_column('ml2_dvr_port_bindings', 'vif_type')
    op.drop_column('ml2_dvr_port_bindings', 'vif_details')
    op.drop_column('ml2_port_bindings', 'vif_type')
    op.drop_column('ml2_port_bindings', 'vif_details')
