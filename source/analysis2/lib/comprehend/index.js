/*********************************************************************************************************************
 *  Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
 *                                                                                                                    *
 *  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://aws.amazon.com/asl/                                                                                    *
 *                                                                                                                    *
 *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

/**
 * @author Solution Builders
 */

'use strict';

let AWS = require('aws-sdk');
let Comprehend = require('./comprehend.js');

module.exports.respond = function(event, cb) {
    let _comprehend = new Comprehend();

    if (event.lambda.function_name == 'get_entities') {
        _comprehend.getEntities(event, function(err, data) {
            if (err) {
                return cb(err, null);
            }
            else {
                return cb(null, data);
            }
        });
    }
    if (event.lambda.function_name == 'get_phrases') {
        _comprehend.getPhrases(event, function(err, data) {
            if (err) {
                return cb(err, null);
            }
            else {
                return cb(null, data);
            }
        });
    }
};
