def label = "worker-${UUID.randomUUID().toString()}"

podTemplate(label: label, namespace: "jenkins", containers: [
  containerTemplate(name: 'python', image: 'python:3.5.1', command: 'cat', ttyEnabled: true)
]) {
  node(label) {
    def myRepo = checkout scm
    stage('Build Docker image') {
      container('python') {
        git 'https://github.com/dfci/cidc-cli/tree/end-to-end'
        sh 'python --version'
        sh 'pip install -r requirements.txt. --no-index'
        sh 'nose2'
      }
    }
  }
}
