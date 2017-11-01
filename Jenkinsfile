#!groovy
@Library('c2c-pipeline-library')
import static com.camptocamp.utils.*

@NonCPS
def getMajorRelease() {
    def majorReleaseMatcher = (env.BRANCH_NAME =~ /^release_(\d+)$/)
    majorReleaseMatcher.matches() ? majorReleaseMatcher[0][1] : ''
}
def majorRelease = getMajorRelease()

env.IN_CI = '1'

// We don't want to publish the same branch twice at the same time.
dockerBuild {
    stage('Update docker') {
        checkout scm
        sh 'make pull'
        sh 'git clean -f -d'
    }
    for (python_version in ['3.5', '']) {
        env.PYTHON_VERSION = python_version

        stage("Build ${python_version}") {
            checkout scm
            sh 'make -j2 build'
        }
        stage("Test ${python_version}") {
            checkout scm
            parallel 'acceptance': {
                try {
                    lock("acceptance-${env.NODE_NAME}") {  //only one acceptance test at a time on a machine
                        sh 'make -j2 acceptance'
                    }
                } finally {
                    if (python_version == '') {
                        junit keepLongStdio: true, testResults: 'reports/*.xml'
                        withCredentials([[$class          : 'UsernamePasswordMultiBinding',
                                          credentialsId   : 'C2cwsgiutilsCodacityToken',
                                          usernameVariable: 'CODACY_PROJECT_USER',
                                          passwordVariable: 'CODACY_PROJECT_TOKEN']]) {
                            sh 'make send_coverage'
                        }
                    }
                }
            }, 'mypy': {
                sh 'make mypy'
            }
        }
    }

    def CURRENT_TAG = sh(returnStdout: true, script: "git fetch --tags && git tag -l --points-at HEAD | tail -1").trim()
    if (CURRENT_TAG != "") {
        if (CURRENT_TAG ==~ /^\d+(?:\.\d+)*$/) {
            parts = CURRENT_TAG.tokenize('.')
            tags = []
            // if the tag is 1.2.3, puts two values in tags: ['1.2', '1.2.3']
            // the major version is managed later another way
            for (int i=2; i<=parts.size(); ++i) {
                curTag = ""
                for (int j = 0; j < i; ++j) {
                    if (j > 0) curTag += '.'
                    curTag += parts[j]
                }
                tags << curTag
            }
        } else {
            tags = [CURRENT_TAG]
        }


        stage("publish ${tags} on docker hub") {
            withCredentials([[$class          : 'UsernamePasswordMultiBinding', credentialsId: 'dockerhub',
                              usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                sh 'docker login -u "$USERNAME" -p "$PASSWORD"'
                for (String tag: tags) {
                    sh "docker tag camptocamp/c2cwsgiutils:latest camptocamp/c2cwsgiutils:${tag}"
                    docker.image("camptocamp/c2cwsgiutils:${tag}").push()
                }
                sh 'rm -rf ~/.docker*'
            }
        }
    }

    if (env.BRANCH_NAME == 'master') {
        stage("publish latest on docker hub") {
            withCredentials([[$class          : 'UsernamePasswordMultiBinding', credentialsId: 'dockerhub',
                              usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                sh 'docker login -u "$USERNAME" -p "$PASSWORD"'
                docker.image('camptocamp/c2cwsgiutils:latest').push()
                sh 'rm -rf ~/.docker*'
            }
        }
    }

    if (majorRelease != '') {
        stage("publish major ${majorRelease} on docker hub") {
            checkout scm
            setCronTrigger('H H(0-8) * * *')
            withCredentials([[$class          : 'UsernamePasswordMultiBinding', credentialsId: 'dockerhub',
                              usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                sh 'docker login -u "$USERNAME" -p "$PASSWORD"'
                sh "docker tag camptocamp/c2cwsgiutils:latest camptocamp/c2cwsgiutils:${majorRelease}"
                docker.image("camptocamp/c2cwsgiutils:${majorRelease}").push()
                sh 'rm -rf ~/.docker*'
            }
        }
    }
}
